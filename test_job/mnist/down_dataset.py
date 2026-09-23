from torchvision import datasets

datasets.MNIST(
    root=".",
    train=True,
    download=True
)

datasets.MNIST(
    root=".",
    train=False,
    download=True
)

print("MNIST dataset downloaded.")