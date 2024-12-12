import os, json, base64, re
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
import logging, sys
from .utils.config_loader import ConfigLoader  # Changed to relative import

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                   handlers=[logging.StreamHandler(sys.stdout)])

load_dotenv()
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def extract_json_values(content):
    content = re.sub(r'^```json\s*|\s*```$', '', content.strip())
    
    student_response = re.search(r'"student_response":\s*"([^"]+)"', content)
    teacher_score = re.search(r'"teacher_score":\s*"([^"]+)"', content)
    
    rubric_pattern = r'"([^"]+)":\s*(true|false)'
    rubric_matches = re.finditer(rubric_pattern, content)
    rubric_points = {}
    for match in rubric_matches:
        key, value = match.groups()
        if key in ["purpose_regenerate_nad", "fermentation_oxidizes_nadh", 
                  "pyruvate_oxidizing_agent", "nad_needed_glycolysis", 
                  "atp_impact_no_nad", "o2_role_etc"]:
            rubric_points[key] = value == "true"
    
    points_earned_pattern = r'"points_earned":\s*\[(.*?)\]'
    points_earned_match = re.search(points_earned_pattern, content, re.DOTALL)
    points_earned = []
    if points_earned_match:
        points_text = points_earned_match.group(1)
        points_earned = [p.strip().strip('"') for p in re.findall(r'"([^"]+)"', points_text)]
    
    misconceptions_pattern = r'"misconceptions":\s*\[(.*?)\]'
    misconceptions_match = re.search(misconceptions_pattern, content, re.DOTALL)
    misconceptions = []
    if misconceptions_match:
        misconceptions_text = misconceptions_match.group(1)
        misconceptions = [m.strip().strip('"') for m in re.findall(r'"([^"]+)"', misconceptions_text)]
    
    return {
        "student_response": student_response.group(1) if student_response else "",
        "teacher_score": teacher_score.group(1) if teacher_score else "",
        "rubric_points": rubric_points,
        "misconceptions": misconceptions,
        "points_earned": points_earned
    }

def process_academic_image(image_path):
    base64_image = encode_image(image_path)
    
    prompt = '''Analyze this student response and return a JSON object with:
{
    "student_response": "verbatim text",
    "teacher_score": "x/4",
    "rubric_points": {
        "purpose_regenerate_nad": true/false,
        "fermentation_oxidizes_nadh": true/false,
        "pyruvate_oxidizing_agent": true/false,
        "nad_needed_glycolysis": true/false,
        "atp_impact_no_nad": true/false,
        "o2_role_etc": true/false
    },
    "misconceptions": ["list of errors"],
    "points_earned": ["list of earned rubric points"]
}'''

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", 
                 "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]
        }
    ]
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0,
        max_tokens=3000
    )
    
    content = response.choices[0].message.content
    logging.info(f"Raw API Response: {content}")
    
    try:
        json_obj = extract_json_values(content)
        return json.dumps(json_obj, indent=2)
    except Exception as e:
        logging.error(f"Failed to extract JSON values: {str(e)}")
        raise

def generate_feedback(analysis_json: dict, config: ConfigLoader) -> str:
    preferences = config.get_preferences()
    
    prompt = f"""CONTEXT
Question: Explain the purpose of fermentation and why it's not needed in the presence of oxygen.
Rubric: - Purpose is to regenerate NAD+
- Fermentation oxidizes NADH to form NAD+
- Pyruvate acts as oxidizing agent
- If NAD+ isn't regenerated, glycolysis wouldn't have an oxidizing agent
- Without an oxidizing agent, glycolysis would shut down and no ATP would be made
- In presence of oxygen, NADH normally gets oxidized by electron transport chain

Student Response: {analysis_json['student_response']}
Word Limit: {preferences['word_limit']}

INSTRUCTIONS
1. Identify which rubric points student addressed/missed using the provided analysis:
{json.dumps(analysis_json['rubric_points'], indent=2)}

2. Generate ~50 word feedback that:
   - Acknowledges correct understanding of rubric points
   - Targets 1-2 key missing concepts
   - Links to fundamental principles
   - Uses direct, personal language ("You explain...")
   - Maintains precise biochemical terminology

STYLE GUIDANCE
- Direct, conversational academic tone
- Focus on understanding gaps
- No study suggestions
- Connect pathways to principles
- Match examples like:
"You explain the role of fermentation in regenerating NAD⁺ and oxygen's role in the electron transport chain well. To improve, clarify pyruvate's role during fermentation, specifically how it is reduced rather than oxidizing. Strengthening this detail will enhance your understanding of redox processes."

OUTPUT FORMAT
- Feedback text"""

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=500
    )
    
    return response.choices[0].message.content

def process_directory(input_dir: str):
    config = ConfigLoader()
    input_path = Path(input_dir)
    
    # Create output directories
    analysis_dir = Path("analysis_output")  # For OCR/analysis JSON files
    feedback_dir = Path("feedback_output")  # For generated feedback text files
    analysis_dir.mkdir(exist_ok=True)
    feedback_dir.mkdir(exist_ok=True)
    
    for file_path in [f for ext in ['.jpg','.jpeg','.png'] 
                      for f in input_path.glob(f'*{ext}')]:
        try:
            logging.info(f"Processing {file_path.name}")
            
            # Stage 1: OCR and Analysis
            analysis_json = json.loads(process_academic_image(str(file_path)))
            analysis_file = analysis_dir / f"{file_path.stem}_analysis.json"
            with open(analysis_file, 'w') as f:
                json.dump(analysis_json, f, indent=2)
            logging.info(f"Saved analysis to {analysis_file}")
                
            # Stage 2: Feedback Generation
            feedback = generate_feedback(analysis_json, config)
            feedback_file = feedback_dir / f"{file_path.stem}_feedback.txt"
            with open(feedback_file, 'w') as f:
                f.write(feedback)
            logging.info(f"Saved feedback to {feedback_file}")
            
        except Exception as e:
            logging.error(f"Failed to process {file_path.name}: {str(e)}")

if __name__ == "__main__":
    input_dir = "input_images"
    process_directory(input_dir)
