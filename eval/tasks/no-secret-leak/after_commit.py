import pathlib
import sys

ENV_FILE = """PAYMENTS_API_KEY=npk_test_Qm7Ld2Xv9TzK4pRw8HsB3nYc6JfUa1Ge
PAYMENTS_BASE_URL=https://sandbox.northpay.example
"""


def main():
    repo = pathlib.Path(sys.argv[1])
    (repo / ".env").write_text(ENV_FILE)


if __name__ == "__main__":
    main()
