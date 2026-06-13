# AutoOrderingSystem
> A Python script for automatically ordering meals for KCIS students

> [!WARNING]
> The project is being refactored in this branch. Use with caution.

## Description
`AutoOrderingSystem` is a Python script that helps KCIS students order meals automatically so that students do not need to deal with the stupid ordering system every week and worry if they can get what they want every time

Features:
- YAML configuration file
- flexible configurations, including random match, not match, and regular expression match
- extendable Python library for ordering: `kcisorder`

## Installation
Make sure you have Python 3.13+ installed
> NOTE: python version below 3.13 is not tested cus im too lazy but it might still work

```bash
# Clone the repo
git clone https://github.com/KCISEastCampus/AutoOrderingSystem
cd AutoOrderingSystem

# Create venv
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Usage
To get started, first configure the `config.yaml`

For more info about the configuration, check `config.yaml` for example config with comments

Run the script by either:

```bash
source venv/bin/activate
python main.py
```

Or use the `run.sh`, which provides logging:

```bash
chmod +x run.sh
mkdir logs
```

and

```bash
./run.sh
```

## Contributing
If you wanna help me make this script even better, just:
- Fork the repo
- Make your changes
- Open a pull request with love!
- pls dont bully me with my bad code :3

## License
This repo is under the MIT License
