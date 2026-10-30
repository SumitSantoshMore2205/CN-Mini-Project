# Subnetting Studio – Visual Network Planner

Browser-based IPv4 subnet calculator built with Streamlit. The web edition contains the calculator, summary metrics, binary reference, subnet allocation table, light/dark appearance toggle, and TXT/CSV downloads. It does not include the desktop topology view.

## Run locally

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Deploy to Streamlit Community Cloud

1. Put the contents of this folder in a GitHub repository.
2. Sign in at [share.streamlit.io](https://share.streamlit.io/) and connect GitHub.
3. Create an app using the repository's default branch and `app.py` as the entrypoint.
4. Deploy. Community Cloud installs the packages listed in `requirements.txt`.

The Python desktop application remains available through `python main.py`.
