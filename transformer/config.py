import transformers


TRAIN_BATCH_SIZE = 64
VALIDATION_BATCH_SIZE = 1
MODEL = "bert-base-uncased"
EPOCHS = 3
MAX_LEN = 256
TOKENIZER = transformers.BertTokenizer.from_pretrained(MODEL, do_lower_case=True)
