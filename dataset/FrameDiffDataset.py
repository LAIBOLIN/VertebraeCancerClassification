# coding: utf-8

import os
import random
import numpy as np
import torch

from torchvision import transforms
from torch.utils.data import DataLoader
from PIL import Image
from tqdm import tqdm


IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

VERTEBRAE_MEAN = [70.7] * 3
VERTEBRAE_STD = [181.5] * 3


class FrameDiff_Dataset(object):
    def __init__(self, root, csv_path, phase, trans=None, balance=True):
        """

        :param root:
        :param trans:
        :param phase:
        """
        with open(csv_path, 'r') as f:
            d = f.readlines()[1:]  # [1:]的作用是去掉表头
            if balance:
                images, labels = [], []
                normal_count = 0
                threshold = 3500 if phase == 'train' else 1230  # training data 取3500个无病的，validation data 取1230个无病的, test data 取所有的
                print("Preparing balanced {} data:".format(phase))
                for x in tqdm(d):
                    image_path = os.path.join(root, str(x).strip().split(',')[0])
                    label = int(str(x).strip().split(',')[1])
                    if phase == 'train' or phase == 'val':
                        if label == 0 and normal_count < threshold:
                            images.append(image_path)
                            labels.append(label)
                            normal_count += 1
                        # elif label in [1, 2, 3]:
                        elif label in [1, 3]:
                            images.append(image_path)
                            labels.append(label)
                        else:
                            pass
                    elif phase == 'test':
                        if label in [0, 1, 3]:
                            images.append(image_path)
                            labels.append(label)
                    elif phase == 'test_output':  # 只用于将每一张test data里的图片的预测结果和label输入到一个文件中
                        images.append(image_path)
                        labels.append(label)
                    else:
                        raise ValueError
            else:
                images = [os.path.join(root, str(x).strip().split(',')[0]) for x in d]
                labels = [int(str(x).strip().split(',')[1]) for x in d]
        self.images = images
        self.labels = labels
        self.phase = phase

        if trans is None:
            if phase == 'train':
                self.trans = transforms.Compose([
                    transforms.RandomHorizontalFlip(),
                    transforms.RandomVerticalFlip(),
                    transforms.RandomRotation(30),
                    transforms.ToTensor(),
                    # transforms.Lambda(lambda x: torch.cat([x] * 3, 0)),
                    transforms.Normalize(mean=VERTEBRAE_MEAN, std=VERTEBRAE_STD)
                ])
            elif phase == 'val' or phase == 'test' or phase == 'test_output':
                self.trans = transforms.Compose([
                    transforms.ToTensor(),
                    # transforms.Lambda(lambda x: torch.cat([x]*3, 0)),
                    transforms.Normalize(mean=VERTEBRAE_MEAN, std=VERTEBRAE_STD)
                ])
            else:
                raise IndexError

    def __getitem__(self, index):
        image_path = self.images[index]

        if index != 0 and index < len(self.images)-1:
            pre_image_path = self.images[index-1]
            next_image_path = self.images[index+1]

            pre_id = pre_image_path.split('/')[8]
            pre_index = int(pre_image_path.split('/')[9].split('_')[1])
            current_id = image_path.split('/')[8]
            current_index = int(image_path.split('/')[9].split('_')[1])
            next_id = next_image_path.split('/')[8]
            next_index = int(next_image_path.split('/')[9].split('_')[1])

            if current_id != pre_id or current_index - pre_index != 1:
                pre_image_path = image_path
            if current_id != next_id or next_index - current_index != 1:
                next_image_path = image_path

        elif index == 0:
            pre_image_path = image_path
            next_image_path = self.images[index+1]

        elif index == len(self.images)-1:
            pre_image_path = self.images[index-1]
            next_image_path = image_path

        else:
            raise IndexError

        # x = np.array([np.load(pre_image_path)])
        # print(x.shape)
        # iamge = Image.fromarray(x)


        # print(pre_image.size, image.size, next_image.size)
        # image = torch.cat([pre_image, image, next_image], dim=0)
        # print(image.size())

        # print(pre_image_path, image_path, next_image_path)

        # 将前后slice的差值加到图像上
        # np_image = np.load(image_path) + (np.load(next_image_path) - np.load(pre_image_path))
        #
        # image = Image.fromarray(np_image)

        pre_image = Image.fromarray(np.load(pre_image_path)).convert('L')
        current_image = Image.fromarray(np.load(image_path)).convert('L')
        next_image = Image.fromarray(np.load(next_image_path)).convert('L')
        image = Image.merge("RGB", (pre_image, current_image, next_image))  # 将前后slice作为三通道merge在一起

        image = self.trans(image)

        label = self.labels[index]

        if label == 3 and self.phase != 'test_output':  # 做分类任务的label必须连续，不能使用[0,1,3]这种label，否则在混淆矩阵处会报错
            label = 2                                   # 对于'test_output'，需要将包括混合型在内的所有直接输出，所以不用调整
        return image, label, image_path

    def __len__(self):
        return len(self.images)

    def dist(self):
        dist = {}
        print("Counting data distribution")
        for l in tqdm(self.labels):
            label = np.load(l)[0]
            if str(int(label)) in dist.keys():
                dist[str(int(label))] += 1
            else:
                dist[str(int(label))] = 1
        return dist


if __name__ == '__main__':
    train_data = FrameDiff_Dataset('/DATA/data/hyguan/liuyuan_spine/data_all/patient_image_4', '/DB/rhome/bllai/PyTorchProjects/Vertebrae/train_path.csv', phase='train', balance=True)
    l = []
    train_dataloader = DataLoader(train_data, batch_size=4, shuffle=True, num_workers=4)
    for i, (img, lab, path) in tqdm(enumerate(train_dataloader)):
        pass
        # l.append(img.squeeze())
    # x = torch.cat(l, 0)
    # print(x.size())
    # print(x.mean(), x.std())


    # image = Image.fromarray(np.load('/DATA/data/hyguan/liuyuan_spine/data_all/patient_image_4/1/1695609/1695609_226/image.npy'))
    # trans = transforms.Compose([transforms.ToTensor(), transforms.Normalize(mean=[16], std=[127])])
    # image = trans(image)
    # print(image.mean(), image.std())
    # print(image.min(), image.max())
    # print(np.mean(image), np.std(image))
    # print(np.min(image), np.max(image))
