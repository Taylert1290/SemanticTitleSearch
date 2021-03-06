from torch import nn
import transformers
import config


class JobMatcherUncased(nn.Module):
    def __init__(self):
        super(JobMatcherUncased, self).__init__()
        self.bert = transformers.BertModel.from_pretrained(config.MODEL)
        self.bert_drop = nn.Dropout(0.3)
        self.out = nn.Linear(768, 1)

    def forward(self, ids, token_type_ids, mask):
        out1, out2 = self.bert(
            ids, token_type_ids=token_type_ids, attention_mask=mask, return_dict=False
        )
        bert_output = self.bert_drop(out2)
        return self.out(bert_output)
