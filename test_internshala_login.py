from dotenv import load_dotenv
from internshala_login import login_to_internshala

load_dotenv()

print(login_to_internshala())