from lib import *
from datasets import load_dataset
import trl
import json
import transformers

# A good chunk of the SFTTrainer code comes from
# https://github.com/huggingface/trl/pull/444#issue-1760952763

model = transformers.AutoModelForCausalLM.from_pretrained("facebook/opt-350m")
tokenizer = transformers.AutoTokenizer.from_pretrained("facebook/opt-350m")
#tokenizer.add_special_tokens({'pad_token': '<pad>'})

# Makes loss calculations ignore the "### Repsonse:" label
response_template = """### Response:
"""
collator = trl.DataCollatorForCompletionOnlyLM(response_template, tokenizer=tokenizer)


def formatting_prompts_func(examples):
    output_text = []

    for i in range(len(examples["instruction"])):
        prompt = examples["instruction"][i]
        input_text = examples["input"][i]
        response = examples["output"][i]
        text = f"""### Instruction:
{prompt}

### Input:
{input_text}

### Response:
{response}"""
        output_text.append(text)
    return output_text

#TODO: This is super inefficient. Maybe I can simplify it?
(con, cur) = initDB()
trainingData = generateTrainingData(con, cur)
dataset_loc = 'db' + os.sep + 'input_output_dataset.json'
# Save this to a json file, then immediately load it for SFTTrainer
with open(dataset_loc, 'w') as f:
    json.dump(trainingData, f)
    f.close()

dataset = load_dataset("json", data_files = dataset_loc)

# Manually split our dataset into 10 distinct 90-10% splits for training/evaluation respectively. This will let us manually cross-validate.
split_dataset = dataset['train'].train_test_split(test_size=0.2)
val_ds = load_dataset("json", data_files = dataset_loc, split=[f"train[{k}%:{k+10}%]" for k in range(0, 100, 10)])
train_ds = load_dataset("json", data_files = dataset_loc, split=[f"train[:{k}%]+train[{k+10}%:]" for k in range(0, 100, 10)])
print("-----")

trainingArgs = transformers.TrainingArguments(
    output_dir= './tmp_trainer',
    num_train_epochs = 10,          # Train for 10 epochs, after which we will consider our best checkpoint to be the final trained model. Increase/decrease this as needed.
    load_best_model_at_end = True,  # Best checkpoint is always saved (counts toward total save limit defined below)
    save_total_limit = 10,          # Saves 10 most recent checkpoints before deleting oldest. Checkpoints are big files, but you can increase this number if you have enough space.
    save_strategy = "epoch",        # Save a checkpoint of the model at the end of each epoch.
    evaluation_strategy = "epoch",  # Evaluate the model at the end of each epoch. This gives us an eval_loss value to determine which checkpoint is the current best.
    logging_strategy = "epoch",     # Make a log at the end of each epoch.
    weight_decay = 0.001,
)

# iterate through our cross-validation dataset splits

for trainerNum, train_dataset, val_dataset in zip(range(10), train_ds, val_ds):
    print(f"Running Trainer {trainerNum+1}")
    trainer = trl.SFTTrainer(
        model,
        args = trainingArgs,
        tokenizer = tokenizer,
        train_dataset = train_dataset,
        eval_dataset = val_dataset,
        formatting_func = formatting_prompts_func,
        max_seq_length = 1024,
        packing = False,
        dataset_batch_size = 16,
        data_collator = collator,
        callbacks=[transformers.EarlyStoppingCallback(early_stopping_patience=2)],  # Stop training with this dataset split if the eval_loss gets worse for n epochs.
    )
    trainer.train()
    trainer.save_model("model.bin")
    print(f"Trainer {trainerNum+1}/10 complete.")
    # At this point, our best model for that dataset split has been saved to "model.bin", so load that as the starting model for our next trainer
    model = "model.bin"

# You can turn this on if your GPU is CUDA-enabled. Only do this if you have a GPU with more memory than your CPU (or a lot of GPUs).
# Be sure to first reinstall pytorch with CUDA via the instructions at https://pytorch.org/get-started/locally/
# model.cuda()
print("-----")

#try:    # Try to resume training from an existing checkpoint
#    print("Attempting to resume training from checkpoint.")
#    trainer.train(resume_from_checkpoint=True)
#except: # If no existing checkpoint exists, start training from scratch
#    print("WARNING - No existing checkpoint found. Training new model from scratch.")
#    trainer.train()

#trainer.save_model("model.bin")