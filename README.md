# Scrap immoweb.be
Retrieve new results for a specific search and send difference with last execution of the script by email.

## Requirements
- Python 3.9
- pip3 installed
- install requirements:
```commandline
pip3 install -r requirements.txt
```

## Config
Open `.env.template` and edit the following variables:
- `SENDER_EMAIL`: email of the sender,
- `MAIL_PASSWORD`: password link to the email of the sender,
- `RECIPIENTS`: list of string containing all the recipients of the emails to be sent.

Then, rename `.env.template` to `.env`.

## Run
```commandline
python3 scrap_immoweb.py
```