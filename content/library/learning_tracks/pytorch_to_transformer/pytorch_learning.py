import torch 
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
dtype = torch.float

d1 = torch.randn(3,2,2, device=device, dtype=dtype)
d2 = torch.zeros(3,3,2, device=device, dtype=dtype)
ad1 = torch.tensor([[1,2,3,4],[2,3,4,5]], device=device)
d3 = torch.cat([d1, d2], dim=1)
print(d3.shape)
print(d3.reshape(3,-1).shape)

# squeeze/unsqueeze
s1 = torch.randn(1,2,3, device=device)
s1_seq = s1.squeeze()
print(s1_seq.shape)
s1_unseq =s1.unsqueeze(3)
print("unsequeeze: ", s1_unseq.shape)

# 广播
x1 = torch.ones(3, 3, 3)
x2 = torch.tensor([1, 1, 3])
print("x1:", x1)
print("x2:", x2, ",x2 shape = ", x2.shape)
x2_new = x2.unsqueeze(0)
print("x2 shape unsequeeze = ", x2_new.shape )

x2_new = x2_new.unsqueeze(1)
print("x2 shape two unsequeeze = ", x2_new.shape )
x3 = x1 + x2
print("x3 :", x3)
x3_2 = x1 + x2_new
print("x3_2 :", x3_2)