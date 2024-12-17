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

def setup_directories():
    """Create necessary directories if they don't exist"""
    dirs = ['input_images', 'analysis_output', 'feedback_output', 'validation_output']
    for dir in dirs:
        Path(dir).mkdir(exist_ok=True)

def print_section_header(title):
    """Print a formatted section header"""
    print("\n" + "="*50)
    print(f" {title}")
    print("="*50)

def print_subsection(title):
    """Print a formatted subsection header"""
    print(f"\n{'-'*3} {title} {'-'*3}")

def get_teacher_inputs():
    """Prompt for assignment details"""
    print_section_header("Setup Grading Session")
    
    # Get question
    question = input("\nEnter assignment question: ")
    
    # Get rubric points
    print("\nEnter rubric points (one per line, empty line to finish):")
    rubric = []
    while True:
        point = input("> ")  # Added prompt indicator
        if not point: break
        rubric.append(point)
    
    # Get grading notes
    print("\nEnter grading notes (one per line, empty line to finish):")
    grading_notes = []
    while True:
        note = input("> ")  # Added prompt indicator
        if not note: break
        grading_notes.append(note)
    
    word_limit = int(input("\nEnter word limit for feedback: "))
    return question, rubric, grading_notes, word_limit

def display_results(filename: str, feedback: str, validation: dict, analysis_json: dict):
    """Display feedback and validation results with improved formatting"""
    print_section_header(f"Results for {filename}")
    
    # Display Score
    print_subsection("Score")
    print(f"Points: {analysis_json['teacher_score']}")
    
    # Display Points Earned
    print_subsection("Points Earned")
    for point in analysis_json['points_earned']:
        print(f"✓ {point}")
    
    # Display Missing Points
    missing_points = [point for point, earned in analysis_json['rubric_points'].items() if not earned]
    if missing_points:
        print_subsection("Missing Points")
        for point in missing_points:
            print(f"✗ {point}")
    
    # Display Misconceptions
    if analysis_json['misconceptions']:
        print_subsection("Misconceptions")
        for misconception in analysis_json['misconceptions']:
            print(f"• {misconception}")
    
    # Display Feedback
    print_subsection("Generated Feedback")
    print(feedback)
    
    # Display Validation Results
    print_subsection("Validation")
    results = validation['validation_results']
    validation_score = validation['validation_score']
    print(f"Quality Score: {validation_score:.0f}%")
    print("Criteria Check:", end=' ')
    for criterion, result in results.items():
        print('✅' if result == 'Y' else '❌', end='')
    print()  # New line after validation icons
    
    # Display any validation failures
    if validation['failed_criteria']:
        print("\nImprovement Needed:")
        for criterion in validation['failed_criteria']:
            explanation = validation['explanations'].get(criterion, "No explanation provided")
            print(f"• {criterion}: {explanation}")
    
    print("\n" + "="*50)  # Section end separator

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

def process_academic_image(image_path, question, rubric_points, grading_notes):
    base64_image = encode_image(image_path)
    
    # Create dynamic rubric JSON structure
    rubric_json = {point: "true/false" for point in rubric_points}
    
    prompt = f'''Analyze this student response and return a JSON object with:
{{
    "student_response": "verbatim text",
    "teacher_score": "x/{len(rubric_points)}",
    "rubric_points": {json.dumps(rubric_json, indent=4)},
    "misconceptions": ["list of errors"],
    "points_earned": ["list of earned rubric points"]
}}

Question: {question}

Grading Notes:
{chr(10).join(f"- {note}" for note in grading_notes)}'''

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

def generate_feedback(analysis_json: dict, config: ConfigLoader, question: str, grading_notes: list, word_limit: int) -> str:
    preferences = config.get_preferences()
    
    prompt = f"""CONTEXT
Question: {question}

Rubric Points Status:
{json.dumps(analysis_json['rubric_points'], indent=2)}

Grading Notes:
{chr(10).join(f"- {note}" for note in grading_notes)}

Student Response: {analysis_json['student_response']}
Word Limit: {word_limit}

INSTRUCTIONS
1. Consider the grading notes when analyzing the response.

2. Identify which rubric points student addressed/missed using the provided analysis:
{json.dumps(analysis_json['rubric_points'], indent=2)}

3. Generate ~{word_limit} word feedback that:
   - Acknowledges correct understanding of rubric points
   - Targets 1-2 key missing concepts
   - Links to fundamental principles
   - Uses direct, personal language ("You explain...")
   - Maintains precise terminology
   - Considers points-for-presence grading approach
   - Addresses any required final point requirements

STYLE GUIDANCE
- Direct, conversational academic tone
- Focus on understanding gaps
- No study suggestions
- Connect concepts to principles
- Match examples like:
"You explain the key concepts well. To improve, clarify [specific point], specifically how it relates to [principle]. Strengthening this detail will enhance your understanding."

OUTPUT FORMAT
- Feedback text"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=500
    )
    
    return response.choices[0].message.content

def extract_validation_json(content: str) -> dict:
    """Helper function to extract JSON from GPT response"""
    content = re.sub(r'^```json\s*|\s*```$', '', content.strip())
    
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                raise ValueError("Could not parse validation response as JSON")
        raise ValueError("No JSON object found in response")

def validate_feedback(feedback_text: str, rubric_points: dict, teacher_config: dict, question: str, grading_notes: list) -> dict:
    """Validates feedback against 8 criteria using GPT-4."""
    prompt = f"""CONTEXT
Question: {question}

Grading Notes:
{chr(10).join(f"- {note}" for note in grading_notes)}

Feedback to Validate: {feedback_text}

Rubric Points Status:
{json.dumps(rubric_points, indent=2)}

Teacher Preferences:
{json.dumps(teacher_config, indent=2)}

INSTRUCTIONS
Evaluate the feedback against these 8 criteria. For each criterion, respond with ONLY "Y" or "N".
If responding with "N", provide a brief explanation why in the explanations section.

VALIDATION CRITERIA:
1. Is the feedback scientifically correct?
2. Does the feedback address at least one rubric-aligned point?
3. Does it avoid irrelevant praise or off-topic details?
4. Is the feedback clear, concise, and professional?
5. Does it guide actionable improvement?
6. Is the feedback tone aligned with teacher preferences?
7. Will this feedback encourage thoughtful improvement?
8. Is the feedback easy to understand and logically structured?

REQUIRED RESPONSE FORMAT:
{{
    "validation_results": {{
        "scientifically_correct": "Y",
        "rubric_aligned": "Y",
        "avoids_irrelevant": "Y",
        "clear_and_professional": "Y",
        "actionable_guidance": "Y",
        "tone_aligned": "Y",
        "encourages_improvement": "Y",
        "well_structured": "Y"
    }},
    "explanations": {{
        "criterion_name": "explanation for N responses only"
    }}
}}

Note: Respond ONLY with the JSON object above. No additional text or formatting."""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=1000
    )
    
    try:
        content = response.choices[0].message.content
        logging.info(f"Validation response: {content}")
        
        validation_data = extract_validation_json(content)
        results = validation_data["validation_results"]
        
        # Calculate validation score
        passed_count = sum(1 for result in results.values() if result == "Y")
        validation_score = (passed_count / 8) * 100
        
        # Get failed criteria
        failed_criteria = [
            criterion for criterion, result in results.items()
            if result == "N"
        ]
        
        return {
            "validation_results": results,
            "failed_criteria": failed_criteria,
            "validation_score": validation_score,
            "explanations": validation_data.get("explanations", {})
        }
    except Exception as e:
        logging.error(f"Validation error: {str(e)}")
        logging.error(f"Raw response: {response.choices[0].message.content}")
        raise

def process_directory(input_dir: str, question: str, rubric_points: list, grading_notes: list, word_limit: int):
    config = ConfigLoader()
    input_path = Path(input_dir)
    
    # Create output directories
    setup_directories()
    
    # Process each image file
    image_files = [f for ext in ['.jpg','.jpeg','.png'] 
                   for f in input_path.glob(f'*{ext}')]
    
    if not image_files:
        print("\nNo image files found in input_images directory!")
        return
    
    print_section_header(f"Processing {len(image_files)} Assignments")
    
    for file_path in image_files:
        try:
            print(f"\nProcessing {file_path.name}...")
            
            # Stage 1: OCR and Analysis
            analysis_json = json.loads(process_academic_image(str(file_path), question, rubric_points, grading_notes))
            analysis_file = Path("analysis_output") / f"{file_path.stem}_analysis.json"
            with open(analysis_file, 'w') as f:
                json.dump(analysis_json, f, indent=2)
                
            # Stage 2: Feedback Generation
            feedback = generate_feedback(analysis_json, config, question, grading_notes, word_limit)
            feedback_file = Path("feedback_output") / f"{file_path.stem}_feedback.txt"
            with open(feedback_file, 'w') as f:
                f.write(feedback)
            
            # Stage 3: Feedback Validation
            validation_results = validate_feedback(
                feedback_text=feedback,
                rubric_points=analysis_json["rubric_points"],
                teacher_config={
                    "preferences": config.get_preferences(),
                    "feedback_criteria": config.get_feedback_criteria()
                },
                question=question,
                grading_notes=grading_notes
            )
            
            validation_file = Path("validation_output") / f"{file_path.stem}_validation.json"
            with open(validation_file, 'w') as f:
                json.dump(validation_results, f, indent=2)
            
            # Display results
            display_results(file_path.name, feedback, validation_results, analysis_json)
            
        except Exception as e:
            logging.error(f"Failed to process {file_path.name}: {str(e)}")
            print(f"\nError processing {file_path.name}. See logs for details.")

if __name__ == "__main__":
    try:
        # Get teacher inputs
        question, rubric_points, grading_notes, word_limit = get_teacher_inputs()
        
        # Process assignments
        process_directory("input_images", question, rubric_points, grading_notes, word_limit)
        
    except KeyboardInterrupt:
        print("\n\nGrading session interrupted by user.")
        sys.exit(0)
    except Exception as e:
        logging.error(f"Application error: {str(e)}")
        print("\nAn error occurred. Please check the logs for details.")
