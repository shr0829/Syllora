
print(f"---------------------------")
import torch

w = torch.randn(1, requires_grad=True)
b = torch.randn(1, requires_grad=True)
 
x = torch.tensor([[1.0], [2.0], [3.0], [4.0]])
y_true = torch.tensor([[3.0], [5.0], [7.0], [9.0]])

lr = 0.1
for epoch in range(20):

    y_pred = w*x + b
    loss = ((y_pred - y_true)**2).mean()
    if w.grad is not None:
        w.grad.zero_()
    if b.grad is not None:
        b.grad.zero_()
    loss.backward()

    with torch.no_grad():
        w -= lr*w.grad
        b -= lr*b.grad

    print(f"epoch={epoch}, loss={loss.item():.4f}, w={w.item():.4f}, b={b.item():.4f}")

print(f"---------------------------")
## 工程写法
import torch
import torch.nn as nn

model = nn.Linear(1, 1)
criterion = nn.MSELoss()
optimizer = torch.optim.SGD(model.parameters(), lr = 0.1)

for epoch in range(20):
    optimizer.zero_grad()
    y_pred_2 = model.forward(x)
    loss = criterion(y_true, y_pred_2)
    loss.backward()
    optimizer.step()
    print(f"epoch={epoch}, loss={loss.item():.4f}, w={w.item():.4f}, b={b.item():.4f}")

