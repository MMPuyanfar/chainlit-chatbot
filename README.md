# chainlit-chatbot

Cloning the project:
```bash
git clone https://github.com/MMPuyanfar/chainlit-chatbot.git
cd chainlit-chatbot
```
Creating a virtual environment and installing the dependencies:
(3.13 >= python version >= 3.12)
```bash
python -m venv .venv
source .venv/bin/activate   # Linux/mac
pip install -r requirements.txt
```

Running the project (run the command in the root directory):
```bash
chainlit run app.py -w
```

If you want to run the tests, first install the test libraries:
```bash
pip install -r test-requirements.txt
```

Then run the tests:
```bash
pytest
```