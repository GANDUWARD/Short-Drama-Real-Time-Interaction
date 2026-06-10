package handler

import (
	"encoding/json"
	"errors"
	"net/http"

	"shortdrama/backend/internal/model"

	"github.com/gin-gonic/gin"
	"gorm.io/datatypes"
	"gorm.io/gorm"
)

type HighlightHandler struct {
	db *gorm.DB
}

type highlightRequest struct {
	EpisodeID   uint64          `json:"episode_id" binding:"required"`
	TriggerTime int             `json:"trigger_time"`
	Duration    int             `json:"duration"`
	EventType   string          `json:"event_type" binding:"required"`
	HeatLevel   int             `json:"heat_level"`
	Payload     json.RawMessage `json:"payload" binding:"required"`
}

func NewHighlightHandler(db *gorm.DB) *HighlightHandler {
	return &HighlightHandler{db: db}
}

func (h *HighlightHandler) Register(rg *gin.RouterGroup) {
	rg.GET("/highlights", h.List)
	rg.GET("/highlights/:id", h.Get)
	rg.POST("/highlights", h.Create)
	rg.PUT("/highlights/:id", h.Update)
	rg.DELETE("/highlights/:id", h.Delete)
}

func (h *HighlightHandler) List(c *gin.Context) {
	var events []model.HighlightEvent
	query := h.db.Order("episode_id asc").Order("trigger_time asc")

	if episodeID := c.Query("episode_id"); episodeID != "" {
		query = query.Where("episode_id = ?", episodeID)
	}
	if eventType := c.Query("event_type"); eventType != "" {
		query = query.Where("event_type = ?", eventType)
	}

	if err := query.Find(&events).Error; err != nil {
		failure(c, http.StatusInternalServerError, err.Error())
		return
	}

	success(c, http.StatusOK, events)
}

func (h *HighlightHandler) Get(c *gin.Context) {
	id, ok := parseID(c)
	if !ok {
		return
	}

	var event model.HighlightEvent
	if err := h.db.First(&event, id).Error; err != nil {
		handleDBError(c, err)
		return
	}

	success(c, http.StatusOK, event)
}

func (h *HighlightHandler) Create(c *gin.Context) {
	var req highlightRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		failure(c, http.StatusBadRequest, err.Error())
		return
	}
	if err := validateHighlightRequest(req); err != nil {
		failure(c, http.StatusBadRequest, err.Error())
		return
	}
	if !h.episodeExists(req.EpisodeID) {
		failure(c, http.StatusBadRequest, "episode_id does not exist")
		return
	}

	event := model.HighlightEvent{
		EpisodeID:   req.EpisodeID,
		TriggerTime: req.TriggerTime,
		Duration:    req.Duration,
		EventType:   req.EventType,
		HeatLevel:   req.HeatLevel,
		Payload:     datatypes.JSON(req.Payload),
	}
	if err := h.db.Create(&event).Error; err != nil {
		failure(c, http.StatusInternalServerError, err.Error())
		return
	}

	success(c, http.StatusCreated, event)
}

func (h *HighlightHandler) Update(c *gin.Context) {
	id, ok := parseID(c)
	if !ok {
		return
	}

	var req highlightRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		failure(c, http.StatusBadRequest, err.Error())
		return
	}
	if err := validateHighlightRequest(req); err != nil {
		failure(c, http.StatusBadRequest, err.Error())
		return
	}
	if !h.episodeExists(req.EpisodeID) {
		failure(c, http.StatusBadRequest, "episode_id does not exist")
		return
	}

	var event model.HighlightEvent
	if err := h.db.First(&event, id).Error; err != nil {
		handleDBError(c, err)
		return
	}

	event.EpisodeID = req.EpisodeID
	event.TriggerTime = req.TriggerTime
	event.Duration = req.Duration
	event.EventType = req.EventType
	event.HeatLevel = req.HeatLevel
	event.Payload = datatypes.JSON(req.Payload)

	if err := h.db.Save(&event).Error; err != nil {
		failure(c, http.StatusInternalServerError, err.Error())
		return
	}

	success(c, http.StatusOK, event)
}

func (h *HighlightHandler) Delete(c *gin.Context) {
	id, ok := parseID(c)
	if !ok {
		return
	}

	if err := h.db.Delete(&model.HighlightEvent{}, id).Error; err != nil {
		failure(c, http.StatusInternalServerError, err.Error())
		return
	}

	success(c, http.StatusOK, gin.H{"id": id})
}

func (h *HighlightHandler) episodeExists(episodeID uint64) bool {
	var count int64
	h.db.Model(&model.Episode{}).Where("id = ?", episodeID).Count(&count)
	return count > 0
}

func validateHighlightRequest(req highlightRequest) error {
	if req.TriggerTime < 0 || req.Duration <= 0 {
		return errors.New("trigger_time must be >= 0 and duration must be > 0")
	}
	if req.HeatLevel < 0 {
		return errors.New("heat_level must be >= 0")
	}
	if !json.Valid(req.Payload) {
		return errors.New("payload must be valid JSON")
	}
	return nil
}
