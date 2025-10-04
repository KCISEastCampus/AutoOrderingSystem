cd "$(dirname "$(realpath "$0")")"
source venv/bin/activate
python main.py | tee "logs/$(date +"%Y_%m_%d_%A_%I_%M_%p")_ordering.log"
deactivate
