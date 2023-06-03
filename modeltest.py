import pandas as pd
from sklearn.model_selection import train_test_split, StratifiedShuffleSplit
from transformers import DebertaTokenizer, DebertaForSequenceClassification, Trainer, TrainingArguments
import torch
import wandb

# Initialize wandb
wandb.init(project="your-project-name")

# load data
df = pd.read_csv('card_info_clean.csv')  # replace with your csv file
df_sampled = df.sample(n=200, random_state=0)  # sample 200 data points
df_sampled.info()
texts = df_sampled['info_sentence'].tolist()
labels = df_sampled['meta'].tolist()

# Split into training and validation before converting to tensors
sss = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=0)
for train_index, val_index in sss.split(texts, labels):
    train_texts = [texts[i] for i in train_index]
    val_texts = [texts[i] for i in val_index]
    train_labels = [labels[i] for i in train_index]
    val_labels = [labels[i] for i in val_index]

# load tokenizer
tokenizer = DebertaTokenizer.from_pretrained('microsoft/deberta-base')

# tokenize data for training set
train_encodings = tokenizer(train_texts, truncation=True, padding=True, max_length=512, return_tensors='pt')
train_encodings['labels'] = torch.tensor(train_labels)

# tokenize data for validation set
val_encodings = tokenizer(val_texts, truncation=True, padding=True, max_length=512, return_tensors='pt')
val_encodings['labels'] = torch.tensor(val_labels)

# Convert encodings to a Dataset format
class CardInfoDataset(torch.utils.data.Dataset):
    def __init__(self, encodings):
        self.encodings = encodings

    def __getitem__(self, idx):
        item = {key: torch.tensor(val[idx]) for key, val in self.encodings.items()}
        return item

    def __len__(self):
        return len(self.encodings['input_ids'])

train_dataset = CardInfoDataset(train_encodings)
val_dataset = CardInfoDataset(val_encodings)

# define the training args
training_args = TrainingArguments(
    output_dir='./results',          
    num_train_epochs=3,              
    per_device_train_batch_size=16,  
    per_device_eval_batch_size=64,   
    warmup_steps=500,                
    weight_decay=0.01,               
    logging_dir='./logs',
    report_to="wandb",
)

# load model with the right number of labels
model = DebertaForSequenceClassification.from_pretrained('microsoft/deberta-base', num_labels=len(set(labels)))

# create the trainer
trainer = Trainer(
    model=model,                         
    args=training_args,                  
    train_dataset=train_dataset,         
    eval_dataset=val_dataset,
)

# Train the model with wandb logging

trainer.train()

wandb.finish()
