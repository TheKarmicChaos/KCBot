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

(con, cur) = initDB()
trainingData = generateTrainingData(con, cur)
# Save this to a json file, then immediately load it for SFTTrainer
with open('db' + os.sep + 'input_output_dataset.json', 'w') as f:
    json.dump(trainingData, f)
    f.close()
dataset = load_dataset("json", data_files = "db" + os.sep + "input_output_dataset.json")
# Split our dataset into a 80-20% split for training/evaluation respectively.
split_dataset = dataset['train'].train_test_split(test_size=0.2, seed=42)
print(split_dataset)
print("-----")



trainingArgs = transformers.TrainingArguments(
    output_dir= './tmp_trainer',
    num_train_epochs = 100,         # Train for 100 epochs, after which we will consider our best checkpoint to be the final trained model. Increase/decrease this as needed.
    load_best_model_at_end = True,  # Best checkpoint is always saved (counts toward total save limit defined below)
    save_total_limit = 10,          # Saves 10 most recent checkpoints before deleting oldest. Checkpoints are big files, but you can increase this number if you have enough space.
    save_strategy = "epoch",        # Save a checkpoint of the model at the end of each epoch.
    evaluation_strategy = "epoch",  # Evaluate the model at the end of each epoch. This gives us a loss value to determine which checkpoint is the current best.
    logging_strategy = "epoch",      # Make a log at the end of each epoch.
    weight_decay = 0.05,
)

trainer = trl.SFTTrainer(
    model,
    args = trainingArgs,
    tokenizer = tokenizer,
    train_dataset = split_dataset['train'],
    eval_dataset = split_dataset['test'],
    formatting_func = formatting_prompts_func,
    max_seq_length = 512,
    packing = False,
    dataset_batch_size = 16,
    data_collator = collator,
)

# You can turn this on if your GPU is CUDA-enabled. Only do this if you have a GPU with more memory than your CPU (or a lot of GPUs).
# Be sure to first install pytorch with CUDA via the instructions at https://pytorch.org/get-started/locally/
# model.cuda()
print("-----")

try:    # Try to resume training from an existing checkpoint
    print("Attempting to resume training from checkpoint.")
    trainer.train(resume_from_checkpoint=True)
except: # If no existing checkpoint exists, start training from scratch
    print("WARNING - No existing checkpoint found. Training new model from scratch.")
    trainer.train()

trainer.save_model("model.bin")