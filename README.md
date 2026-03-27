# Job Link Screenshot Agent

A Python agent that reads job URLs from an Excel file, opens each one in a browser, takes a screenshot, and sends all results to your email. Failed URLs are listed with the reason they failed.

---

## Why I Chose Option 1

I chose Option 1 because it covers a complete automation workflow from start to finish. Reading a file, controlling a browser, handling errors, and delivering output over email felt like a realistic and well-rounded problem to solve. It also made it easy to show how the agent handles broken or inaccessible links without crashing.

---

## Demo Video

Link: https://youtu.be/jAH7v74Ri0c?si=pCUUNVzL0erCgVpj


---

## Project Files

- job_screenshot_agent.py — the main script that runs everything
- option1_job_links.xlsx — the input Excel file with 5 job URLs
- requirements.txt — the list of Python libraries to install
- screenshots/ — folder that gets created automatically when the agent runs
- README.md — this file

---

## Setup and Installation

### What you need before starting

- Python 3.11 or higher (download from https://python.org/downloads)
- A Gmail account with 2-Step Verification turned on


### Step 1 - Install the required libraries

    pip install -r requirements.txt
    playwright install chromium

The second command downloads a small browser that the agent uses in the background. It only needs to be run once.

### Step 2 - Set up your credentials


Open the .env file and fill in these three lines:

    EMAIL_SENDER=your_gmail@gmail.com
    EMAIL_PASSWORD=your16characterpassword
    EMAIL_RECEIVER=whoever_gets_the_email@example.com

To get a Gmail App Password:
- Go to https://myaccount.google.com/apppasswords
- Make sure 2-Step Verification is on
- Click Create a new app password and give it any name
- Copy the 16-character code it gives you
- Paste it into EMAIL_PASSWORD with no spaces

### Step 3 - Run the agent

    python job_screenshot_agent.py

### Step 4 - Check your email

You will get an email with screenshots embedded in the body and a table showing which URLs failed and why.

---

## How It Works

The agent runs in three stages.

First, it reads the Excel file using pandas and pulls out the five job URLs. It ignores the Status and Notes columns and treats every URL as an unknown input.

Second, it opens a hidden Chrome browser using a library called Playwright. It visits each URL one at a time, scrolls the page to load any content that only appears on scroll, then takes a full-page screenshot and saves it as a PNG file. Each URL is wrapped in its own error handler so if one fails, the rest still get processed.

Third, it sends an email using Gmail. The screenshots are embedded directly in the email body so you can see them without opening attachments. Any URLs that failed are shown in a table with the exact error message.

---

## What to Expect from the Input File

- Job 1, Anthropic - the page loads and a screenshot is captured
- Job 2, Amazon - the page loads and a screenshot is captured
- Job 3, Figma - the page loads and a screenshot is captured
- Job 4, TechCorp (Fake) - the domain does not exist, DNS error is caught and reported
- Job 5, LinkedIn - the page redirects to a login screen, this is caught and reported

---

## Assumptions

- Gmail is used for sending email. If you use Outlook or another provider the SMTP settings would need to change.
- The agent only processes rows in the Excel file that have a URL starting with http.
- The Status and Notes columns are ignored completely. The agent does not read them.
- If a page loads but shows a login wall, a screenshot is still taken. It will just show the login page.
- The machine running the script has a stable internet connection.

---

## What I Would Improve Given More Time

- Add a retry system so pages that time out get tried one more time before being marked as failed.
- Detect when a page redirected to a login screen and report it separately from a full failure.
- Add Microsoft Teams as a delivery option alongside email.
- Run all five URLs at the same time instead of one after another to make it faster.
- Write a log file for each run so there is a record even if the email is deleted.

---

## Dependencies

- pandas - reads the Excel input file
- openpyxl - required by pandas to open xlsx files
- playwright - controls the browser and takes screenshots
- python-dotenv - reads the .env file so credentials stay out of the code
