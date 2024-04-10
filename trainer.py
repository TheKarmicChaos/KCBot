from lib import *
from datasets import load_dataset
from trl import SFTTrainer
import json
import transformers

# A large chunk of the SFT code comes from
# https://github.com/huggingface/trl/pull/444#issue-1760952763

try:        #if a model already exists, we want to resume training from that model
    model = transformers.AutoModelForCausalLM.from_pretrained("model.bin")
except:
    print("WARNING - No model found, using default opt-350 model (ignore this if it is your first time training)")
    model = transformers.AutoModelForCausalLM.from_pretrained("facebook/opt-350m")
tokenizer = transformers.AutoTokenizer.from_pretrained("facebook/opt-350m")

def formatting_prompts_func(examples):
    output_text = []
    
    for i in range(len(examples["instruction"])):
        prompt = examples["instruction"][i]
        input_text = examples["input"][i]
        response = examples["output"][i]

        text = f"""Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.
        
        ### Instruction:\n{prompt}
        
        ### Input:\n{input_text}
        
        ### Response:\n{response}
        """
        output_text.append(text)

    return output_text

(con, cur) = initDB()
trainingData = generateTrainingData(con, cur)
# Save this to a json file, then immediately load it for SFTTrainer
with open('db' + os.sep + 'input_output_dataset.json', 'w') as f:
    json.dump(trainingData, f)
    f.close()
dataset = load_dataset("json", data_files = "db" + os.sep + "input_output_dataset.json", split="train")

trainer = SFTTrainer(
    model,
    tokenizer = tokenizer,
    train_dataset = dataset,
    formatting_func = formatting_prompts_func,
    max_seq_length = 512,
    packing = False,
    dataset_batch_size = 16
)

#formattedTrainingData = formatting_prompts_func(trainingData) #uncomment this to view dataset for debugging

#model.cuda() #you can turn this on if you have a good GPU for training
trainer.train()

trainer.save_model("model.bin")