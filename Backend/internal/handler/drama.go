package handler

import (
	"net/http"
	"strconv"

	"shortdrama/backend/internal/model"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

type DramaHandler struct {
	db *gorm.DB
}

type dramaRequest struct {
	Title       string `json:"title" binding:"required"`
	Description string `json:"description"`
	CoverURL    string `json:"cover_url"`
}

func NewDramaHandler(db *gorm.DB) *DramaHandler {
	return &DramaHandler{db: db}
}

func (h *DramaHandler) Register(rg *gin.RouterGroup) {
	rg.GET("/dramas", h.List)
	rg.GET("/dramas/:id", h.Get)
	rg.POST("/dramas", h.Create)
	rg.PUT("/dramas/:id", h.Update)
	rg.DELETE("/dramas/:id", h.Delete)
}

func (h *DramaHandler) List(c *gin.Context) {
	var dramas []model.Drama
	if err := h.db.Order("id desc").Find(&dramas).Error; err != nil {
		failure(c, http.StatusInternalServerError, err.Error())
		return
	}
	success(c, http.StatusOK, dramas)
}

func (h *DramaHandler) Get(c *gin.Context) {
	id, ok := parseID(c)
	if !ok {
		return
	}

	var drama model.Drama
	err := h.db.Preload("Episodes", func(db *gorm.DB) *gorm.DB {
		return db.Order("episode_no asc")
	}).First(&drama, id).Error
	if err != nil {
		handleDBError(c, err)
		return
	}

	success(c, http.StatusOK, drama)
}

func (h *DramaHandler) Create(c *gin.Context) {
	var req dramaRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		failure(c, http.StatusBadRequest, err.Error())
		return
	}

	drama := model.Drama{
		Title:       req.Title,
		Description: req.Description,
		CoverURL:    req.CoverURL,
	}
	if err := h.db.Create(&drama).Error; err != nil {
		failure(c, http.StatusInternalServerError, err.Error())
		return
	}

	success(c, http.StatusCreated, drama)
}

func (h *DramaHandler) Update(c *gin.Context) {
	id, ok := parseID(c)
	if !ok {
		return
	}

	var req dramaRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		failure(c, http.StatusBadRequest, err.Error())
		return
	}

	var drama model.Drama
	if err := h.db.First(&drama, id).Error; err != nil {
		handleDBError(c, err)
		return
	}

	drama.Title = req.Title
	drama.Description = req.Description
	drama.CoverURL = req.CoverURL

	if err := h.db.Save(&drama).Error; err != nil {
		failure(c, http.StatusInternalServerError, err.Error())
		return
	}

	success(c, http.StatusOK, drama)
}

func (h *DramaHandler) Delete(c *gin.Context) {
	id, ok := parseID(c)
	if !ok {
		return
	}

	if err := h.db.Delete(&model.Drama{}, id).Error; err != nil {
		failure(c, http.StatusInternalServerError, err.Error())
		return
	}

	success(c, http.StatusOK, gin.H{"id": id})
}

func parseID(c *gin.Context) (uint64, bool) {
	id, err := strconv.ParseUint(c.Param("id"), 10, 64)
	if err != nil {
		failure(c, http.StatusBadRequest, "invalid id")
		return 0, false
	}
	return id, true
}

func handleDBError(c *gin.Context, err error) {
	if err == gorm.ErrRecordNotFound {
		failure(c, http.StatusNotFound, "resource not found")
		return
	}
	failure(c, http.StatusInternalServerError, err.Error())
}
