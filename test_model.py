import torch
import custom_models as cst
import os
import auxiliaries as aux
from torchvision import transforms
from torch.utils.data import DataLoader
from sklearn.metrics import accuracy_score
from tqdm import tqdm
import torch.nn as nn

# Parameters
splits_folder='train_test_split3'    # Name of the folder that contains the txt files for the splits 
model_save_name = 'model_inception_make_16_focal_1.pt'  # Name of the model
model_name,classification_type,batch_size,loss_name=model_save_name.split('.')[0].split('_')[1:-1]  # Extract parameters of the model to reconstruct it
batch_size = int(batch_size)    # Convert to int

# Just like in the other files
root_dir = os.path.join(os.getcwd(), '../CompCars/data/cropped_image')
file_paths_test = os.path.join(os.getcwd(), f'../CompCars/data/{splits_folder}/classification/test.txt')

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# Transformations
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# Dataset and DataLoader creation
dataset = aux.CustomImageDataset(root_dir=root_dir, file_paths=file_paths_test,
                                 classification_type=classification_type, 
                                 transform=transform, train=False)
test_loader = DataLoader(dataset, batch_size=batch_size, shuffle=False)

# Number of classes based on classification type
if classification_type == 'make':
    num_classes = 163
elif classification_type == 'model':
    num_classes = 1712
else:
    raise ValueError("Unsupported classification type. Use 'make' or 'model'.")

# Create model equal to the one we want to load
if model_name=='inception':
    model = cst.InceptionV1(in_channels=3, num_classes=num_classes).to(device)
elif model_name=='resnet18':
    model = cst.ResNet(cst.ResidualBlock, [2, 2, 2, 2],num_classes=num_classes).to(device)
elif model_name=='resnet-simple':
    model = cst.ResNet(cst.ResidualBlock, [1, 1, 1, 1],num_classes=num_classes).to(device)
else:
    print('Unsupported model')

# Loss definition, based on the one used during training
if loss_name=='focal':    
    criterion = aux.FocalLoss()
elif loss_name=='cross-entropy':
    criterion = nn.CrossEntropyLoss()
else:
    print('Unsupported loss')

# Load model and move to device
model.load_state_dict(torch.load(os.path.join(os.getcwd(), model_save_name), map_location=device))

# Set in evaluation mode
model.eval()

# Initialize variables for tracking
all_preds = []
all_labels = []
total_loss = 0.0

# Evaluation
with torch.no_grad():
    for images, labels in tqdm(test_loader, desc="Testing"):
        #Move to device
        images, labels = images.to(device), labels.to(device)
        
        # Calculate loss
        outputs = model(images)
        loss = criterion(outputs, labels)
        total_loss += loss.item() * labels.size(0)  # Multiply by batch size for total loss 
                                                    #(its not exactly right, the last batch
                                                    # might not be exactly of batch_size)
        
        # Get predictions
        _, preds = torch.max(outputs, 1)  # Get the predicted class indices
        all_preds.extend(preds.cpu().numpy())
        all_labels.extend(labels.cpu().numpy())

# Calculate metrics
accuracy = accuracy_score(all_labels, all_preds)
average_loss = total_loss / len(dataset)

# Print results
print(f"Test Loss: {average_loss}")
print(f"Test Accuracy: {accuracy * 100}%")
