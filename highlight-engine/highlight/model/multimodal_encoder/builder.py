import os

from .clip_encoder import CLIPVisionTower
#########################################################################################
from .time_encoder import TimeTower, TimeTokenizer
from .score_encoder import ScoreTower, ScoreTokenizer
from .sync_encoder import SyncTower
#########################################################################################


def resolve_vision_tower_name(vision_tower):
    override = os.environ.get("HIGHLIGHT_VISION_TOWER_PATH")
    if override:
        return override

    if os.path.exists(vision_tower):
        return vision_tower

    # Some released Highlight checkpoints store the CLIP tower as a relative local path
    # like "model/clip-vit-large-patch14-336". If that folder is not present locally,
    # fall back to the public Hugging Face identifier for the same CLIP model.
    if vision_tower.startswith("model/"):
        repo_name = vision_tower.split("/", 1)[1]
        return f"openai/{repo_name}"

    return vision_tower

def build_vision_tower(vision_tower_cfg, **kwargs):
    vision_tower = getattr(vision_tower_cfg, 'mm_vision_tower', getattr(vision_tower_cfg, 'vision_tower', None))
    vision_tower = resolve_vision_tower_name(vision_tower)

    is_absolute_path_exists = os.path.exists(vision_tower)
    if  vision_tower.startswith("openai") or vision_tower.startswith("laion") or 'clip' in vision_tower:
        vision_tower = CLIPVisionTower(vision_tower, args=vision_tower_cfg, **kwargs)
    else:
        raise ValueError(f'Unknown vision tower: {vision_tower}')

    return vision_tower

#########################################################################################

def build_time_tower(pretrain_tokenizer, pretrained_embedding_weights, dim):

    time_tokenizer = TimeTokenizer()

    time_tower = TimeTower(time_tokenizer,pretrain_tokenizer=pretrain_tokenizer, hidden_dim=dim, pretrain_embedding=pretrained_embedding_weights)

    return time_tokenizer, time_tower

def build_score_tower(pretrain_tokenizer, pretrained_embedding_weights, dim):

    score_tokenizer = ScoreTokenizer()

    score_tower = ScoreTower(score_tokenizer, pretrain_tokenizer=pretrain_tokenizer, hidden_dim=dim, pretrain_embedding=pretrained_embedding_weights)

    return score_tokenizer, score_tower

def build_sync_tower(dim):


    sync_tower = SyncTower(hidden_dim=dim)

    return sync_tower

#########################################################################################
