import torch
import torch.nn as nn
import torch.optim as optim
import torchvision.transforms as transforms
import torchvision.models as models
from CelebA import CelebA
import os
from torch.autograd import Variable
import argparse
from torch.optim.lr_scheduler import *

transform_train = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomHorizontalFlip(),
    transforms.ToTensor(),
    transforms.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225)),
])

transform_val = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225)),
])

parser = argparse.ArgumentParser()
parser.add_argument('--workers', type=int, default=2)
parser.add_argument('--batchSize', type=int, default=32)
parser.add_argument('--nepoch', type=int, default=10)
parser.add_argument('--lr', type=float, default=2e-6)
parser.add_argument('--gpu', type=str, default='7', help='gpu ids: e.g. 0  0,1,2, 0,2. use -1 for CPU')
opt = parser.parse_args()
print(opt)

os.environ["CUDA_VISIBLE_DEVICES"] = opt.gpu

trainset = CelebA('/content/list_eval_partition.csv', '/content/list_attr_celeba.csv', '0',
                  '/content/img_align_celeba/img_align_celeba/', transform_train)

trainloader = torch.utils.data.DataLoader(trainset, batch_size=opt.batchSize, shuffle=True, num_workers=opt.workers)

valset = CelebA('/content/list_eval_partition.csv', '/content/list_attr_celeba.csv', '1',
                  '/content/img_align_celeba/img_align_celeba/', transform_val)
valloader = torch.utils.data.DataLoader(valset, batch_size=opt.batchSize, shuffle=True, num_workers=opt.workers)


#model = resnet50(pretrained=True, num_classes=40)
model=models.resnet50(pretrained=True)
model.fc=nn.Linear(2048,40)
model.cuda()
criterion = nn.BCEWithLogitsLoss(reduce=True)
optimizer = optim.Adam(model.parameters(), lr=opt.lr)
scheduler = StepLR(optimizer, step_size=2, gamma=0.5)


def train(epoch):
    print('\nTrain epoch: %d' % epoch)
    model.train()
    for batch_idx, (images, attrs) in enumerate(trainloader):
        images = Variable(images.cuda())
        attrs = Variable(attrs.cuda()).type(torch.cuda.FloatTensor)
        optimizer.zero_grad()
        output = model(images)
        loss = criterion(output, attrs)
        loss.backward()
        optimizer.step()
        if batch_idx%100==0:
            print('[%d/%d][%d/%d] loss: %.4f' % (epoch, opt.nepoch, batch_idx, len(trainloader), loss.mean()))
    scheduler.step()



def test(epoch):
    print('\nTest epoch: %d' % epoch)
    model.eval()
    correct = torch.FloatTensor(40).fill_(0)
    total = 0
    with torch.no_grad():
        for batch_idx, (images, attrs) in enumerate(valloader):
            images = Variable(images.cuda())
            attrs = Variable(attrs.cuda()).type(torch.cuda.FloatTensor)
            output = model(images)
            com1 = output > 0
            com2 = attrs > 0
            correct.add_((com1.eq(com2)).data.cpu().sum(0).type(torch.FloatTensor))
            total += attrs.size(0)
    print(correct / total)
    print(torch.mean(correct / total))



for epoch in range(0, opt.nepoch):
    train(epoch)
    test(epoch)
torch.save(model.state_dict(), 'model_naive.pth')
