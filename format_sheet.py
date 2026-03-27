from dotenv import load_dotenv
load_dotenv()

from src.formatter import format_sheet

print("Formatting Google Sheet...")
format_sheet()
