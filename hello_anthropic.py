"""Hello-world test for the Anthropic SDK.

Run:
    python hello_anthropic.py
"""

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()


def main() -> None:
    client = Anthropic()

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=200,
        messages=[
            {"role": "user", "content": "Say hello in one short sentence."}
        ],
    )

    for block in response.content:
        if block.type == "text":
            print(block.text)

    print(
        f"\n[input tokens: {response.usage.input_tokens}, "
        f"output tokens: {response.usage.output_tokens}]"
    )


if __name__ == "__main__":
    main()