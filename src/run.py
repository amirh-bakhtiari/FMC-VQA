# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.14.0
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# + tags=[]
import numpy as np
import torch
from torchvision import models
from torchvision import transforms
from pathlib import Path
from tqdm import tqdm
from torchvision.models.feature_extraction import create_feature_extractor

import DatasetHandler as dh
import pooling
import regression as reg
import SFVQA as sfv
import VideoUtility as vu


# + tags=[]
def videoset_frame_feats(model, device, video_list: str, video_path: str, transform, 
                         dataset: str = 'LIVE', *, frame_diff=False) -> list:
    '''Get the VQA dataset video names and scores, set a feature extractor model,
       get frames of each video, then get features of each frame in videos
       
    :param video_list: list of video sequences name
    :param video_path: videos' directory
    :param transform: preprocessing pipeline
    :param dataset: name of the VQA dataset to extract the features from
    :param fine_tune: use fine-tuned model if True
    :return: videos' frames features of dimension and videos scores (DMOS)
    '''
    
    # feature_extractor = create_feature_extractor(model, return_nodes=['6.7.add'])
    # Convert the path string to a pathlib object
    video_path = Path(video_path)
    dataset = dataset.lower()
    # videos_frame_features = []
    for seq in tqdm(video_list):
        # Concatenate the video sequence name to the video directory to get the full video path
        vid_path = str(video_path / seq)
        if dataset == 'live':
            # Get frames of the video of the dimension 768 * 432 (LIVE VQA videos)
            vid_frames = vu.get_frames(vid_path, height=432, width=768)
        else:
            vid_frames = vu.get_frames(vid_path, frame_diff=frame_diff)
        # Get the features of all frames of the video
        frames_features = sfv.get_video_style_features(vid_frames, model, device, transform)
        frames_features = np.array(frames_features)
        # videos_frame_features.append(frames_features)
        yield frames_features
    
    # return videos_frame_features, scores


# -

def video_level_feats(ffeats_extractor, dfeats_extractor, device, dataset, frame_size, center_crop,
                      frame_diff: bool = False, pool_type='max'):
    '''Get frame level features and pool them to have video level features (representation)
    
    :param model: feature extractor model object
    :param device: torch.device for torch tensors, which can be of cuda or cpu type
    :param dataset: VQA dataset, to extract its frames'features
    :param layers: layers in extractor model to get frame features from
    :param diff_layer: layers in extractor model to get feats of consecutive frames' differences from
    :prama frame_size: the size to which frames are resized
    :param center_crop: the size to crop a center patch from the resized frame
    :param frame_diff: indicate if features of frame differences are required
    :param pool_type: for simple pooling, the method of pooling frame level feats of a video
    :return: pooled frame features of videos, video quality scores 
    
    '''
    
    # Get the list of videos and corresponding scores and preprocessing module of cross dataset
    video_list, scores, transform, video_path = dh.get_videoset_info(dataset=dataset,
                                                                     frame_size=frame_size,
                                                                     center_crop=center_crop)
    # Get frame features of all videos in the dataset --------------------------------------*
    videos_features = videoset_frame_feats(ffeats_extractor, device, video_list, video_path, 
                                           transform, dataset)
    # Pool the frame level features to get video level features
    pooled_features = pooling.simple_pooling(videos_features, pool_type=pool_type)
    
    if frame_diff:
        diff_features = videoset_frame_feats(dfeats_extractor, device, video_list, video_path, transform,
                                             dataset, frame_diff=frame_diff)
        # Pool the frame level features to get video level features
        pooled_diff = pooling.simple_pooling(diff_features, pool_type=pool_type)
        
        # Concatenate the pooled features from frames and frame differences
        pooled_features = np.concatenate((pooled_features, pooled_diff), axis=1)
    
    return pooled_features, scores


# + tags=[]
def init_vqa(model_name, vqa_dataset, cross_dataset=None, frame_diff=False):
    ''' Set the frame feature extractor model, VQA dataset and frame size
    
    :param model_name: name of the feature extractor model, 'inceptionv3', 'vgg19':
    :param vqa_dataset: VQA dataset to evaluate the method on, 'KONVID1K' , 'LIVE'
    :return: model, dataset and frame size and patch
    '''
    
    if model_name == 'vgg19':
        frame_size, center_crop = 255, 224
        # Specify the layers to get style features from vgg19
        layers = {
                  # 'features.10': 'conv3_1',
                  'features.16': 'conv3_4',
                  # 'features.19': 'conv4_1',
                  # 'features.21': 'conv4_2',
                  'avgpool': 'avgpool'
                  }
        # Layer for getting features from frame differences
        diff_layer = {'features.20': 'conv4_2'}
        
    elif model_name == 'inceptionv3':
        frame_size, center_crop = 338, 299
        # Specify the layers to get style features from inceptionv3
        layers = {
                  # 'Conv2d_1a_3x3': 'conv1_1',
                  # 'Conv2d_3b_1x1': 'conv2_1', 
                  'Mixed_5b': 'Mixed_1', 
                  # 'Mixed_5c': 'Mixed_2',
                  'avgpool': 'avgpool'
                  }
        # Layer for getting features from frame differences
        diff_layer = {'avgpool': 'avgpool'}
    
    # EfficientNet B4 layers
    elif model_name == 'efficientnet':
        frame_size, center_crop = 423, 380
        # Specify the layers to get style features from EfficientNet B4
        layers = {
                  'features.3.3.add': 'features.3.3.add',
                  'features.4.4.add': 'features.4.4.add',
                  'features.5.5.add': 'features.5.5.add',
                  'avgpool': 'avgpool',
                  }
        # Layer for getting features from frame differences
        diff_layer = {
                      # 'features.5.5.add': 'features.5.5.add',
                      'avgpool': 'avgpool',
                     }        
    
    
    # Check if there is a GPU
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    # Set the frame features extractor model
    ffeats_extractor, dfeats_extractor = sfv.set_feats_extractor(device, model_name, layers, diff_layer,
                                                                 fine_tune=False, frame_size=frame_size,
                                                                 center_crop=center_crop)
                
    return ffeats_extractor, dfeats_extractor, device, vqa_dataset, cross_dataset, frame_size,\
                                                                        center_crop, frame_diff    


# -

# Entry point of the program
def main():
    '''Run the whole process of VQA
    '''
    # Initialize vqa
    ffeats_extractor, dfeats_extractor, device, vqa_dataset, cross_dataset, frame_size, center_crop,\
                                                                   frame_diff = init_vqa('efficientnet', 
                                                                                         'konvid1k')
    # Get video level features by pooling frame level features
    pooled_feats, scores = video_level_feats(ffeats_extractor, dfeats_extractor, device, vqa_dataset,
                                             frame_size, center_crop, frame_diff)
    
    if cross_dataset:
        # Get video level features by pooling features of consecutive frames' differences
        c_pooled_feats, c_scores = video_level_feats(ffeats_extractor, dfeats_extractor, device,
                                                     cross_dataset, frame_size, center_crop, frame_diff)
    else:
        c_pooled_feats, c_scores = None, None
        
    # Train a regressor using video level features and indicate how well it predicts the scores
    reg.regression(pooled_feats, scores, c_pooled_feats, c_scores, 'svr', vqa_dataset, cross_dataset)               


# + tags=[]
# Run the main function if current file is the script, not a module
if __name__ == "__main__":
    main()
# -












