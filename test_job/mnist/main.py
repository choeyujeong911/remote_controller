import time

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms


# =========================
# Configuration
# =========================

EPOCHS = 20
BATCH_SIZE = 64
LEARNING_RATE = 0.001

torch.manual_seed(42)

device = torch.device("cpu")


# =========================
# Dataset
# =========================

transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.1307,), (0.3081,))
])

train_dataset = datasets.MNIST(
    root=".",
    train=True,
    download=False,
    transform=transform
)

test_dataset = datasets.MNIST(
    root=".",
    train=False,
    download=False,
    transform=transform
)

train_loader = DataLoader(
    train_dataset,
    batch_size=BATCH_SIZE,
    shuffle=True
)

test_loader = DataLoader(
    test_dataset,
    batch_size=1000,
    shuffle=False
)


# =========================
# Model
# =========================

class MNISTCNN(nn.Module):

    def __init__(self):
        super().__init__()

        self.conv1 = nn.Conv2d(1, 32, 3, 1)
        self.conv2 = nn.Conv2d(32, 64, 3, 1)

        self.pool = nn.MaxPool2d(2)

        self.fc1 = nn.Linear(64 * 12 * 12, 128)
        self.fc2 = nn.Linear(128, 10)

        self.relu = nn.ReLU()

    def forward(self, x):

        x = self.relu(self.conv1(x))
        x = self.relu(self.conv2(x))

        x = self.pool(x)

        x = torch.flatten(x, 1)

        x = self.relu(self.fc1(x))
        x = self.fc2(x)

        return x


model = MNISTCNN().to(device)

criterion = nn.CrossEntropyLoss()

optimizer = optim.Adam(
    model.parameters(),
    lr=LEARNING_RATE
)


# =========================
# Training
# =========================

print("=== MNIST Training ===")
print(f"Device: {device}")
print(f"Epochs: {EPOCHS}")
print(f"Batch size: {BATCH_SIZE}")
print(f"Training samples: {len(train_dataset)}")
print()

start_time = time.perf_counter()

for epoch in range(1, EPOCHS + 1):

    model.train()

    total_loss = 0.0

    for images, labels in train_loader:

        images = images.to(device)
        labels = labels.to(device)

        optimizer.zero_grad()

        outputs = model(images)

        loss = criterion(outputs, labels)

        loss.backward()

        optimizer.step()

        total_loss += loss.item()

    average_loss = total_loss / len(train_loader)

    print(
        f"Epoch {epoch:02d}/{EPOCHS} "
        f"- Loss: {average_loss:.4f}"
    )


training_time = time.perf_counter() - start_time


# =========================
# Test
# =========================

model.eval()

correct = 0
total = 0

test_start = time.perf_counter()

with torch.no_grad():

    for images, labels in test_loader:

        images = images.to(device)
        labels = labels.to(device)

        outputs = model(images)

        predictions = outputs.argmax(dim=1)

        correct += (predictions == labels).sum().item()
        total += labels.size(0)


test_time = time.perf_counter() - test_start
accuracy = 100.0 * correct / total
torch.save(model.state_dict(), "mnist_model.pt")
print("Model saved: mnist_model.pt")

# =========================
# Result
# =========================

print()
print("=== Result ===")
print(f"Accuracy: {accuracy:.2f}%")
print(f"Training time: {training_time:.2f} sec")
print(f"Test time: {test_time:.2f} sec")
print(f"Total compute time: {training_time + test_time:.2f} sec")