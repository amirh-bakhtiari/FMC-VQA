def get_csiq_info(file_path: str) -> list:
    '''Get CSIQ VQA dataset metadata file and extract video file names and their 
       corresponding DMOS
    
    :param file_path: the path to the video dataset metadata file
    :return: list of video names, and their DMOS
    '''
    with open(file_path, 'r') as f:
        videos ,dmos = [], []
        # Skip the 1st line of the file which includes titles
        for i, line in enumerate(f):
            if i == 0:
                continue
            videos.append(line.split()[0])
            dmos.append(float(line.split()[1]))
    
    return videos, dmos

def get_live_info(video_file: str, dmos_file: str) -> list:
    '''Get LIVE VQA dataset metadata files and extract video file names and their 
       corresponding DMOS
    
    :param video_file: the path to the video sequence names file
    :param dmos_file: the path to the dmos file
    :return: list of video names, and their DMOS
    '''
    
    with open(video_file, 'r') as vid_file, open(dmos_file, 'r') as dmos_file:
        # Get the name of video sequences
        videos = vid_file.read().split('\n')
        # Get the DMOS of each video
        scores = dmos_file.read().split('\n')
        dmos = [float(score.split('\t')[0]) for score in scores]
    
    return videos, dmos   
    

def prepare_videoset(dataset='LIVE', frame_size: int = 224, center_crop: int = 224, framework='pytorch', **kwargs):
    '''Given the name of the video dataset, get the list of respective video names and their scores,
       and set the preprocessing method.
       
    :param dataset: name of a VQA dataset
    :param frame_size: frame size according to the input of the pretrained model
    :param center_crop: used to crop the frame if frame_size is bigger than input of the model
    :param framework: deep learning framework
    :param **kwargs: file names containing the info about videos and scores of a dataset
    :return: list of video names, their scores and the preprocessing module
    '''

    if dataset == 'LIVE':
        videos, scores = get_live_info(kwargs['video_file'], kwargs['dmos_file'])
    elif dataset == 'CSIQ':
        videos, scores = get_csiq_info(kwargs['video_file'])
        
    
    if framework == 'pytorch':
        # pytorch specific preprocessing
        # values of means and stds in Normalize are the ones used for ImageNet
        frm_transform = transforms.compose([transforms.Resize(frame_size),
                                            transforms.CenterCrop(center_crop),
                                            transforms.ToTensor(),
                                            transforms.Normalize((0.485, 0.456, 0.406),
                                                                 (0.229, 0.224, 0.225))])
    elif framework == 'keras':
        ## TODO
        pass
    
    
    return videos, scores, frm_transform

def live_vqa_regression():
    '''
    '''
    
    