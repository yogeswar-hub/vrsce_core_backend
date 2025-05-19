import logging
from com.dimcon.synthera.utilities.log_handler import LoggerManager

logger = LoggerManager.setup_logger(__name__, level=logging.DEBUG)

class JsonService:
    @staticmethod
    def parse_event(event):
        try:
            # Step 1: Get meeting ID
            meeting_id = event.get("meeting_id")
            if not meeting_id:
                logger.error("Missing 'meeting_id' in event.")
                raise ValueError("Missing 'meeting_id' in event.")
            logger.info("Parsed meeting_id: %s", meeting_id)

            # Step 2: Get answers dictionary
            answers = event.get("answers")
            if not answers or not isinstance(answers, dict):
                logger.error("Missing or invalid 'answers' in event.")
                raise ValueError("Missing or invalid 'answers' in event.")

            # Step 3: Extract question-answer pairs with proper question numbers
            extracted_data = {
                "meeting_id": meeting_id,
                "answers": []
            }
            
            """ Example of expected answers dictionary:
{
  'meeting_id': 'CHIME12345',
  'answers': [
    {'question_number': 1, 'question_id': 'Q1', 'question_text': 'What is the timeline?', 'answer_text': '6 months'},
    {'question_number': 3, 'question_id': 'Q3', 'question_text': 'What is the budget?', 'answer_text': '$500,000'}
  ]
}
"""

            for key in sorted(answers.keys()):
                #sorted_keys becomes: ['A1', 'A2', 'Q1', 'Q2'] (alphabetical)
                if key.startswith("Q") and key[1:].isdigit():
                    question_id = key           # e.g., "Q3"
                    answer_id = "A" + key[1:]   # → "A3"
                    question_number = int(key[1:])  # → 3
                    question_text = answers.get(question_id)
                    answer_text = answers.get(answer_id)

                    if not answer_text:
                        logger.warning("No answer found for question %s", question_id)
                        continue

                    extracted_data["answers"].append({
                        "question_number": question_number,
                        "question_id": question_id,
                        "question_text": question_text,
                        "answer_text": answer_text
                    })

            logger.info("Extracted structured data: %s", extracted_data)
            return extracted_data

        except Exception as e:
            logger.error("Error parsing event: %s", str(e), exc_info=True)
            raise
