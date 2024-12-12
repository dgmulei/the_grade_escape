# The Grade Escape

An automated feedback system for grading student assignments with OCR and GPT-4 Vision.

## Features
- OCR processing of handwritten assignments
- Rubric-based analysis
- Personalized feedback generation
- Three-stage processing: analysis, feedback, and validation
- Configurable teacher preferences
- Automated feedback quality validation
- Interactive CLI interface for batch processing

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
│   ├── academic_processor.py  # Main processing script with CLI interface
│   ├── config/               # Teacher preferences and feedback settings
│   │   ├── josh_preferences.json     # Feedback style and tone settings
│   │   └── josh_feedback_insights.json # Rubric and validation rules
│   └── utils/                # Helper functions
│       └── config_loader.py  # Configuration management
├── input_images/            # Place student assignments here
├── analysis_output/         # Stage 1: OCR and rubric analysis results
├── feedback_output/         # Stage 2: Generated student feedback
├── validation_output/       # Stage 3: Feedback validation results
└── requirements.txt         # Project dependencies
```

## Usage
1. Place student assignments (jpg/jpeg/png) in `input_images/` directory
2. Run the grading interface:
```bash
python -m src.academic_processor
```
3. Follow the CLI prompts:
   - Enter the assignment question
   - Input rubric points (one per line, empty line to finish)
   - Specify word limit for feedback
4. The system will process all assignments and display:
   - Individual feedback for each submission
   - Validation results with checkmark/cross indicators (✅/❌)
   - Save all results to respective output directories

## Processing Stages
1. **Analysis Stage**
   - OCR processes handwritten assignments using GPT-4 Vision
   - Generates detailed rubric analysis
   - Outputs: `analysis_output/*_analysis.json`

2. **Feedback Stage**
   - Uses analysis results and teacher preferences
   - Generates personalized feedback
   - Outputs: `feedback_output/*_feedback.txt`

3. **Validation Stage**
   - Validates generated feedback against 8 quality criteria
   - Ensures alignment with teacher preferences
   - Outputs: `validation_output/*_validation.json`

## Configuration
Edit files in `src/config/` to modify:
- Teacher preferences (`josh_preferences.json`)
  - Feedback tone and style
  - Word limits
  - Preferred phrases
  - Feedback structure guidelines
  - Topics to avoid
- Feedback insights (`josh_feedback_insights.json`)
  - Rubric evaluation rules
  - Validation criteria
  - Grading notes
  - Special scoring rules

## Validation Criteria
The system automatically validates generated feedback against:
1. Scientific accuracy
2. Rubric alignment
3. Relevance and conciseness
4. Clarity and professionalism
5. Actionable guidance
6. Tone alignment
7. Improvement encouragement
8. Logical structure

## Batch Processing
- Handles 10-20 assignments per batch efficiently
- Provides progress updates during processing
- Graceful error handling for individual assignments
- Keyboard interrupt support (Ctrl+C) to stop processing

## Dependencies
- OpenAI API (GPT-4 Vision)
- Python 3.7+
- python-dotenv
