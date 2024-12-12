# The Grade Escape

An automated feedback system for grading student assignments with OCR and GPT-4 Vision.

## Features
- OCR processing of handwritten assignments
- Rubric-based analysis
- Personalized feedback generation
- Two-stage processing: analysis and feedback
- Configurable teacher preferences

## Setup
1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create `.env` file with:
```
OPENAI_API_KEY=your_key_here
```

## Project Structure
```
the_grade_escape/
├── src/
│   ├── academic_processor.py  # Main processing script
│   ├── config/               # Teacher preferences and feedback settings
│   └── utils/                # Helper functions
├── input_images/            # Place student assignments here
├── analysis_output/         # Stage 1: OCR and rubric analysis results
├── feedback_output/         # Stage 2: Generated student feedback
└── requirements.txt         # Project dependencies
```

## Processing Stages
1. **Analysis Stage**
   - OCR processes handwritten assignments
   - Generates detailed rubric analysis
   - Outputs: `analysis_output/*_analysis.json`

2. **Feedback Stage**
   - Uses analysis results and teacher preferences
   - Generates personalized feedback
   - Outputs: `feedback_output/*_feedback.txt`

## Usage
1. Place student assignments (jpg/jpeg/png) in `input_images/` directory
2. Run:
```bash
python -m src.academic_processor
```

## Configuration
Edit files in `src/config/` to modify:
- Teacher preferences (`josh_preferences.json`)
  - Feedback tone and style
  - Word limits
  - Preferred phrases
- Feedback insights (`josh_feedback_insights.json`)
  - Rubric evaluation rules
  - Validation criteria
  - Grading notes

## Dependencies
- OpenAI API
- Python 3.7+
- python-dotenv
