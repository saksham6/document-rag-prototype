import torch
from transformers import AutoTokenizer, AutoModel


class TextEmbedder:
    def __init__(self, model_name: str):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)

    def mean_pooling(self, model_output, attention_mask):
        token_embeddings = model_output[0]
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()

        return torch.sum(token_embeddings * input_mask_expanded, dim=1) / torch.clamp(
            input_mask_expanded.sum(dim=1), min=1e-9
        )

    def encode(self, texts):
        encoded_input = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            return_tensors="pt"
        )

        with torch.no_grad():
            model_output = self.model(**encoded_input)

        embeddings = self.mean_pooling(model_output, encoded_input["attention_mask"])
        embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)

        return embeddings.cpu().numpy()
