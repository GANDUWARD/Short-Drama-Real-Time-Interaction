package model

type Episode struct {
	ID         uint64           `json:"id" gorm:"primaryKey;autoIncrement"`
	DramaID    uint64           `json:"drama_id" gorm:"not null;uniqueIndex:idx_drama_episode_no"`
	EpisodeNo  int              `json:"episode_no" gorm:"not null;uniqueIndex:idx_drama_episode_no"`
	VideoURL   string           `json:"video_url" gorm:"size:500;not null"`
	Duration   int              `json:"duration" gorm:"not null"`
	Highlights []HighlightEvent `json:"highlights,omitempty" gorm:"constraint:OnUpdate:CASCADE,OnDelete:CASCADE;"`
}

func (Episode) TableName() string {
	return "episode"
}
