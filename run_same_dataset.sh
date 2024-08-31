# pip installs
# pip install streamlit
# pip install scikit-learn
# pip install plotly
# export SKLEARN_ALLOW_DEPRECATED_SKLEARN_PACKAGE_INSTALL=True
# pip install sklearn
# pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ submodlib
# pip install sentence-transformers
# pip install faiss-gpu
# pip install peft
# pip install evaluate
# pip install torch
# pip install transformers
# pip install trl
# pip install bert-score
# pip install numpy

### RUN EXPERIMENTS FOR OUR METHODOLOGY ###

# conda activate env3.10

# use case 1: Given a dataset, fine-tune a model on a subset of points that improves the performance on the entire dataset.
python3 visualization/create_embeddings.py --use_case 1
MODEL_NAME='microsoft/Phi-3-mini-4k-instruct'
python3 visualization/load_all_experiments.py --existing_data_name mix-instruct --new_data_name mix-instruct --model_name=$MODEL_NAME
python3 visualization/load_all_experiments.py --existing_data_name natural_instructions --new_data_name natural_instructions --model_name=$MODEL_NAME
python3 visualization/load_all_experiments.py --existing_data_name P3 --new_data_name P3 --model_name=$MODEL_NAME

notify "oh no - same"

### RUN EXPERIMENTS FOR BASELINE ###