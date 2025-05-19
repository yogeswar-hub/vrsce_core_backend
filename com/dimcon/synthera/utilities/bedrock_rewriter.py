import json
import boto3
import logging
from botocore.exceptions import BotoCoreError, ClientError

# Setup module-level logger
logger = logging.getLogger(__name__)


class BedrockRewriter:
    """
    A utility class that rewrites or polishes short-form answers
    into client-ready business paragraphs using Amazon Bedrock Claude 3 (Messages API).
    """

    def __init__(self):
        """
        Initialize the Bedrock runtime client.
        """
        try:
            self.bedrock_client = boto3.client('bedrock-runtime')
            logger.info("Bedrock client initialized successfully.")
        except Exception as e:
            logger.error("Failed to initialize Bedrock client: %s", e, exc_info=True)
            raise

    def rewrite(self, raw_text: str) -> str:
        """
        Submit the given answer to the Claude 3 model for rewriting.

        Parameters:
            raw_text (str): A short or raw answer from the original SOW payload.

        Returns:
            str: A polished and professional paragraph suitable for SOW documentation.
        """
        if not raw_text or not raw_text.strip():
            logger.warning("Empty or null input text provided to rewrite function.")
            return "No answer available."

        try:
            logger.debug("Sending text to Bedrock Claude 3 for rewriting: %s", raw_text)

            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "You are a professional SOW writer.\n"
                            "Please rewrite the following answer as a polished, client-ready paragraph:\n\n"
                            f"{raw_text.strip()}"
                        )
                    }
                ],
                "max_tokens": 1000,
                "temperature": 0.3,
                "top_p": 0.9
            })

            response = self.bedrock_client.invoke_model(
                modelId='anthropic.claude-3-haiku-20240307-v1:0',
                body=body,
                accept='application/json',
                contentType='application/json'
            )

            body_bytes = response.get('body', None)
            if body_bytes is None:
                logger.error("Bedrock response body is missing.")
                return raw_text

            result = json.loads(body_bytes.read())

            # Claude 3 Messages API: 'content' is a list of message parts
            content = result.get("content", [])
            if not content or not isinstance(content, list) or "text" not in content[0]:
                logger.warning("Claude 3 returned unexpected or empty content structure.")
                return raw_text

            polished_text = content[0]["text"].strip()
            logger.debug("Rewriting complete. Result: %s", polished_text)
            return polished_text

        except (BotoCoreError, ClientError) as aws_err:
            logger.error("AWS error occurred while invoking Bedrock: %s", aws_err, exc_info=True)
            return raw_text

        except json.JSONDecodeError as json_err:
            logger.error("Failed to parse Bedrock response JSON: %s", json_err, exc_info=True)
            return raw_text

        except Exception as e:
            logger.error("Unexpected error during Bedrock rewriting: %s", e, exc_info=True)
            return raw_text  # Graceful fallback
