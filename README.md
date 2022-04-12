# QueryMerakiAPI

It's just a program to make requests to Meraki's API and creates a *CSV* with the next columns for each Access Point:
- Network
- Device
- Serial
- Model
- Status
- IP
- Gateway
- Public IP
- DNS
- Usage sentKbps last day
- Usage receivedKbps last day

## Requirements
- [python-dotenv](https://pypi.org/project/python-dotenv/)

## Run
> python main.py

To use it you must provide the API Key and Organization ID, it can be written during the program execution or creating a .env 
file next to the script file with the next content:
> API_KEY = 'YourAPIKey'  
> ORG_ID = 'YourOrganizationID'

---
`<3 SG`
