package model

import "gorm.io/datatypes"

type HighlightEvent struct {
	ID          uint64         `json:"id" gorm:"primaryKey;autoIncrement"`
	EpisodeID   uint64         `json:"episode_id" gorm:"not null;index:idx_episode_trigger"`
	TriggerTime int            `json:"trigger_time" gorm:"not null;index:idx_episode_trigger"`
	Duration    int            `json:"duration" gorm:"not null"`
	EventType   string         `json:"event_type" gorm:"size:50;not null;index"`
	HeatLevel   int            `json:"heat_level" gorm:"not null"`
	Payload     datatypes.JSON `json:"payload" gorm:"type:json"`
}

func (HighlightEvent) TableName() string {
	return "highlight_event"
}
