package model

type Drama struct {
	ID          uint64    `json:"id" gorm:"primaryKey;autoIncrement"`
	Title       string    `json:"title" gorm:"size:255;not null"`
	Description string    `json:"description"`
	CoverURL    string    `json:"cover_url" gorm:"size:500"`
	Episodes    []Episode `json:"episodes,omitempty" gorm:"constraint:OnUpdate:CASCADE,OnDelete:CASCADE;"`
}

func (Drama) TableName() string {
	return "drama"
}
