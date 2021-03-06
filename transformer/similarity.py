import config
from model import JobMatcherUncased
import data_setup
import numpy as np
import pandas as pd

from transformers import AdamW, get_linear_schedule_with_warmup
import torch
from torch import nn
from tqdm import tqdm


class SemanticSimilarity:
    def __init__(self, epochs: int = 2, retrain: bool = True):

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.epochs = epochs
        self.save_path = "model/"
        self.model = JobMatcherUncased()

        if retrain:
            self.model.to(self.device)
        else:
            self.model.load_state_dict(
                torch.load(
                    self.save_path + "LAST_MODEL.model", map_location=self.device
                )
            )

    def loss(self, outputs, targets):
        return nn.BCEWithLogitsLoss()(outputs, targets.view(-1, 1))

    def fit(self, X, y):

        train_dataset = data_setup.JobMatchDataset(
            input1=X["Free Form"], input2=X["Job"], target=y
        )

        train_data_loader = torch.utils.data.DataLoader(
            train_dataset, batch_size=config.TRAIN_BATCH_SIZE, num_workers=4
        )

        param_optimizer = list(self.model.named_parameters())

        no_decay = ["bias", "LayerNorm.bias", "LayerNorm.weight"]

        optimizer_parameters = [
            {
                "params": [
                    p for n, p in param_optimizer if not any(nd in n for nd in no_decay)
                ],
                "weight_decay": 0.001,
            },
            {
                "params": [
                    p for n, p in param_optimizer if any(nd in n for nd in no_decay)
                ],
                "weight_decay": 0.0,
            },
        ]

        num_train_steps = int(len(X) / config.TRAIN_BATCH_SIZE * self.epochs)
        optimizer = AdamW(optimizer_parameters, lr=3e-5)
        scheduler = get_linear_schedule_with_warmup(
            optimizer, num_warmup_steps=0, num_training_steps=num_train_steps
        )

        self.model.train()

        for epoch in range(self.epochs):
            for batch_idx, dataset in tqdm(
                enumerate(train_data_loader), total=len(train_data_loader)
            ):

                ids = dataset["ids"]
                mask = dataset["mask"]
                token_type_ids = dataset["token_type_ids"]
                targets = dataset["targets"]

                ids = ids.to(self.device, dtype=torch.long)
                mask = mask.to(self.device, dtype=torch.long)
                token_type_ids = token_type_ids.to(self.device, dtype=torch.long)
                targets = targets.to(self.device, dtype=torch.float)

                optimizer.zero_grad()
                outputs = self.model(ids, mask=mask, token_type_ids=token_type_ids)
                loss = self.loss(outputs, targets)
                loss.backward()
                optimizer.step()
                scheduler.step()

        torch.save(
            self.model.state_dict(), "{}/LAST_MODEL.model".format(self.save_path)
        )

        def predict(self, X):
            final_outputs = []
            self.model.eval()

            val_dataset = data_setup.JobMatchDataset(
                input1=X["Free Form"], input2=X["Job"], target=np.ones(len(X))
            )

            val_data_loader = torch.utils.data.DataLoader(
                val_dataset, batch_size=config.VALIDATION_BATCH_SIZE, num_workers=4
            )

            with torch.no_grad():
                for batch_idx, dataset in tqdm(
                    enumerate(val_data_loader), total=len(val_data_loader)
                ):

                    ids = dataset["ids"]
                    mask = dataset["mask"]
                    token_type_ids = dataset["token_type_ids"]

                    ids = ids.to(self.device, dtype=torch.long)
                    mask = mask.to(self.device, dtype=torch.long)
                    token_type_ids = token_type_ids.to(self.device, dtype=torch.long)

                    outputs = self.model(ids, mask=mask, token_type_ids=token_type_ids)
                    final_outputs.extend(
                        torch.sigmoid(outputs.cpu()).detach().numpy().tolist()[0]
                    )
            return final_outputs


if __name__ == "__main__":
    df = pd.read_csv(
        "/output_matches/top_matches_flatten.csv"
    )
    l_df = data_setup.melt(df, thresh=0.9)
    X = l_df.drop(["label"], axis=1)
    y = list(l_df["label"])

    clf = SemanticSimilarity(epochs=2, retrain=True)
    clf.fit(X, y)
