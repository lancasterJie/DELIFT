from visualization import load_subset_experiment, calculate_test_performance
from data_object import DataObject, DataObjectConstants
from folder_names import FolderNames
from plotting import Plotting
from models import Models
import numpy as np
import argparse
import pickle
import os

def main(model_names, existing_data_name, new_data_name, threshold, subset_percentage):
    # all experimental configurations
    uc_labels = ["SelectIT", "Model Dependent + CG FL", "Model Independent + CG FL", "Random", "Full Dataset"]
    ucl_shorthand = ["select_it", "mod_dep_fl", "mod_ind_fl", "random", "full_data"] 
    # uc_labels = ["Model Dependent ICL Utility", "Model Dependent Gradient Utility", "Model Independent", "Random", "Full Dataset"]
    # ucl_shorthand = ["mod_dep_icl", "mod_dep_grad", "mod_ind", "random", "full_data"]
    sl_labels = ["ICL", "PEFT"]


    # loop through each of the model names
    for model_name in model_names:
        if existing_data_name == new_data_name:
            fn = FolderNames(model_name, "same_data_cache")
        elif "benchmark" in new_data_name:
            fn = FolderNames(model_name, "benchmark_cache")
        else:
            fn = FolderNames(model_name, "version_cache")

        models = Models(language_model_name=model_name)

        with open(fn.visualization_cache_file, 'rb') as f:
            vis_dims, all_data = pickle.load(f)
        
        labels = [label.split('.')[0] for label in os.listdir(fn.dataset_pkl_folder) if 'all_data' not in label]
        existing_data_ind = labels.index(existing_data_name)
        new_data_ind = labels.index(new_data_name)

        # set up training and validation sets for the DataObject instance
        num_exist_train, num_new_train = len(all_data[existing_data_ind][0]), len(all_data[new_data_ind][0])
        num_exist_valid, num_new_valid = len(all_data[existing_data_ind][1]), len(all_data[new_data_ind][1])
        exist_point_labels = [np.array([f"{existing_data_ind}-{i}" for i in range(len(all_data[existing_data_ind][0]))]), 
                            np.array([f"{existing_data_ind}-{num_exist_train+i}" for i in range(len(all_data[existing_data_ind][1]))]),
                            np.array([f"{existing_data_ind}-{num_exist_train+num_exist_valid+i}" for i in range(len(all_data[existing_data_ind][2]))]),]
        new_point_labels = [np.array([f"{new_data_ind}-{i}" for i in range(len(all_data[new_data_ind][0]))]), 
                            np.array([f"{new_data_ind}-{num_new_train+i}" for i in range(len(all_data[new_data_ind][1]))]),
                            np.array([f"{new_data_ind}-{num_new_train+num_new_valid+i}" for i in range(len(all_data[new_data_ind][2]))])]
    
        # create a DataObject instance
        if existing_data_name == new_data_name:
            data = DataObject(existing_data_name, existing_data_ind, new_data_name, new_data_ind, all_data[existing_data_ind], vis_dims[existing_data_ind], exist_point_labels,
                        all_data[new_data_ind], vis_dims[new_data_ind], new_point_labels,
                        case=DataObjectConstants.DATA_OBJECT_SAME_DATSET)
        elif "benchmark" in new_data_name:
            data = DataObject(existing_data_name, existing_data_ind, new_data_name, new_data_ind, all_data[existing_data_ind], vis_dims[existing_data_ind], exist_point_labels,
                        all_data[new_data_ind], vis_dims[new_data_ind], new_point_labels,
                        case=DataObjectConstants.DATA_OBJECT_BENCHMARK)
        else:
            data = DataObject(existing_data_name, existing_data_ind, new_data_name, new_data_ind, all_data[existing_data_ind], vis_dims[existing_data_ind], exist_point_labels,
                        all_data[new_data_ind], vis_dims[new_data_ind], new_point_labels,
                        case=DataObjectConstants.DATA_OBJECT_NEW_VERSION)
        
        # define the dataset configuration code (a code that indicates the combination of datasets one is using)
        dataset_config_code = fn.dataset_config_file_code(existing_data_name, new_data_name)
        data.set_dataset_config_code(dataset_config_code)

        # create a Plotting instance
        plotting = Plotting(data, labels, models, fn)

        # loop through all combinations of experiments
        for subset_learning in sl_labels:
            for utility_criteria in uc_labels:
                
                # define the experiment configuration (a shorthand code that helps store experiment results in the cache)
                # exp_config = ucl_shorthand[uc_labels.index(utility_criteria)] + "-" + subset_learning + "-" + str(subset_percentage)
                # print('NEW EXPERIMENT\n', exp_config, utility_criteria, '\n\n\n\n')
                # load_subset_experiment(existing_data_name, existing_data_ind, new_data_name, new_data_ind, exp_config, utility_criteria, subset_learning, 
                #                     subset_percentage, threshold, labels, data, plotting, models, fn)
                # calculate_test_performance(all_data[new_data_ind][2], data, exp_config, models, fn, score="rouge")
                try:
                    exp_config = ucl_shorthand[uc_labels.index(utility_criteria)] + "-" + subset_learning + "-" + str(subset_percentage)
                    print('NEW EXPERIMENT\n', exp_config, utility_criteria, '\n\n\n\n')
                    load_subset_experiment(existing_data_name, existing_data_ind, new_data_name, new_data_ind, exp_config, utility_criteria, subset_learning, 
                                        subset_percentage, threshold, labels, data, plotting, models, fn)
                    calculate_test_performance(all_data[new_data_ind][2], data, exp_config, models, fn, score="rouge")
                except Exception as e:
                    with open('failures.txt', 'a+') as f:
                        f.write(exp_config)
                        f.write('\n\n')
                        f.write(str(e))
                        f.write('\n---------------------------------------------------------------------\n')

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=float, default=0.7)
    parser.add_argument("--subset_percentage", type=float, default=0.3)
    parser.add_argument("--existing_data_name", type=str, default="mix-instruct")
    parser.add_argument("--new_data_name", type=str, default="benchmark_mmlu")
    parser.add_argument("--model_name", type=str, default="microsoft/Phi-3-mini-4k-instruct") #microsoft/Phi-3-mini-4k-instruct
    args = parser.parse_args()

    main([args.model_name], args.existing_data_name, args.new_data_name, args.threshold, args.subset_percentage)

