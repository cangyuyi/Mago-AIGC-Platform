package handler

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"mago-agent/api-gateway/internal/model"
	"mago-agent/api-gateway/internal/pkg/response"
	"mago-agent/api-gateway/internal/service"
)

type CharacterHandler struct{ svc *service.CharacterService }

func NewCharacterHandler(svc *service.CharacterService) *CharacterHandler {
	return &CharacterHandler{svc: svc}
}

func (h *CharacterHandler) List(c *gin.Context) {
	uid := getUserID(c)
	page, pageSize := response.GetPagination(c)
	cs, total, err := h.svc.ListByOwner(uid, page, pageSize)
	if err != nil {
		response.InternalError(c, err.Error())
		return
	}
	response.Paginated(c, cs, total, page, pageSize)
}
func (h *CharacterHandler) Create(c *gin.Context) {
	var ch model.Character
	if err := c.ShouldBindJSON(&ch); err != nil {
		response.BadRequest(c, err.Error())
		return
	}
	uid := getUserID(c)
	ch.OwnerID = uid
	if err := h.svc.Create(&ch); err != nil {
		response.InternalError(c, err.Error())
		return
	}
	c.JSON(http.StatusCreated, ch)
}
func (h *CharacterHandler) GetByID(c *gin.Context) {
	id, err := uuid.Parse(c.Param("id"))
	if err != nil {
		response.BadRequest(c, "invalid id")
		return
	}
	ch, err := h.svc.GetByOwner(id, getUserID(c))
	if err != nil {
		response.NotFound(c, "character not found")
		return
	}
	response.Success(c, ch)
}
func (h *CharacterHandler) Update(c *gin.Context) {
	id, err := uuid.Parse(c.Param("id"))
	if err != nil {
		response.BadRequest(c, "invalid id")
		return
	}
	var ch model.Character
	if err := c.ShouldBindJSON(&ch); err != nil {
		response.BadRequest(c, err.Error())
		return
	}
	ch.ID = id
	if err := h.svc.UpdateOwned(&ch, getUserID(c)); err != nil {
		response.NotFound(c, "character not found")
		return
	}
	response.Success(c, ch)
}
func (h *CharacterHandler) Delete(c *gin.Context) {
	id, err := uuid.Parse(c.Param("id"))
	if err != nil {
		response.BadRequest(c, "invalid id")
		return
	}
	if err := h.svc.DeleteOwned(id, getUserID(c)); err != nil {
		response.NotFound(c, "character not found")
		return
	}
	response.Success(c, gin.H{"deleted": true})
}
func (h *CharacterHandler) AddImage(c *gin.Context) {
	var img model.CharacterRefImage
	if err := c.ShouldBindJSON(&img); err != nil {
		response.BadRequest(c, err.Error())
		return
	}
	charID, err := uuid.Parse(c.Param("id"))
	if err != nil {
		response.BadRequest(c, "invalid id")
		return
	}
	img.CharacterID = charID
	if _, err := h.svc.GetByOwner(charID, getUserID(c)); err != nil {
		response.NotFound(c, "character not found")
		return
	}
	if err := h.svc.AddImage(&img); err != nil {
		response.InternalError(c, err.Error())
		return
	}
	c.JSON(http.StatusCreated, img)
}
func (h *CharacterHandler) ListImages(c *gin.Context) {
	charID, err := uuid.Parse(c.Param("id"))
	if err != nil {
		response.BadRequest(c, "invalid id")
		return
	}
	if _, err := h.svc.GetByOwner(charID, getUserID(c)); err != nil {
		response.NotFound(c, "character not found")
		return
	}
	imgs, err := h.svc.ListImages(charID)
	if err != nil {
		response.InternalError(c, err.Error())
		return
	}
	response.Success(c, imgs)
}

func (h *CharacterHandler) DeleteImage(c *gin.Context) {
	imageId, err := uuid.Parse(c.Param("imageId"))
	if err != nil {
		response.BadRequest(c, "invalid image id")
		return
	}
	if err := h.svc.DeleteImageOwned(imageId, getUserID(c)); err != nil {
		response.InternalError(c, err.Error())
		return
	}
	response.Success(c, gin.H{"deleted": true})
}

type StyleHandler struct{ svc *service.StyleService }

func NewStyleHandler(svc *service.StyleService) *StyleHandler { return &StyleHandler{svc: svc} }

func (h *StyleHandler) List(c *gin.Context) {
	uid := getUserID(c)
	category := c.DefaultQuery("category", "all")
	page, pageSize := response.GetPagination(c)
	ss, total, err := h.svc.List(uid, category, page, pageSize)
	if err != nil {
		response.InternalError(c, err.Error())
		return
	}
	response.Paginated(c, ss, total, page, pageSize)
}
func (h *StyleHandler) Create(c *gin.Context) {
	var s model.StylePreset
	if err := c.ShouldBindJSON(&s); err != nil {
		response.BadRequest(c, err.Error())
		return
	}
	uid := getUserID(c)
	s.OwnerID = &uid
	if err := h.svc.Create(&s); err != nil {
		response.InternalError(c, err.Error())
		return
	}
	c.JSON(http.StatusCreated, s)
}
func (h *StyleHandler) GetByID(c *gin.Context) {
	id, err := uuid.Parse(c.Param("id"))
	if err != nil {
		response.BadRequest(c, "invalid id")
		return
	}
	s, err := h.svc.GetVisibleByOwner(id, getUserID(c))
	if err != nil {
		response.NotFound(c, "style not found")
		return
	}
	response.Success(c, s)
}
func (h *StyleHandler) Update(c *gin.Context) {
	id, err := uuid.Parse(c.Param("id"))
	if err != nil {
		response.BadRequest(c, "invalid id")
		return
	}
	var s model.StylePreset
	if err := c.ShouldBindJSON(&s); err != nil {
		response.BadRequest(c, err.Error())
		return
	}
	s.ID = id
	if err := h.svc.UpdateOwned(&s, getUserID(c)); err != nil {
		response.NotFound(c, "style not found")
		return
	}
	response.Success(c, s)
}
func (h *StyleHandler) Delete(c *gin.Context) {
	id, err := uuid.Parse(c.Param("id"))
	if err != nil {
		response.BadRequest(c, "invalid id")
		return
	}
	if err := h.svc.DeleteOwned(id, getUserID(c)); err != nil {
		response.NotFound(c, "style not found")
		return
	}
	response.Success(c, gin.H{"deleted": true})
}
func (h *StyleHandler) Categories(c *gin.Context) {
	uid := getUserID(c)
	cats, err := h.svc.Categories(uid)
	if err != nil {
		response.InternalError(c, err.Error())
		return
	}
	response.Success(c, cats)
}

type AssetHandler struct {
	sceneSvc *service.SceneService
	propSvc  *service.PropService
}

func NewAssetHandler(sceneSvc *service.SceneService, propSvc *service.PropService) *AssetHandler {
	return &AssetHandler{sceneSvc: sceneSvc, propSvc: propSvc}
}
func (h *AssetHandler) ListScenes(c *gin.Context) {
	category := c.DefaultQuery("category", "all")
	page, pageSize := response.GetPagination(c)
	ss, total, err := h.sceneSvc.List(getUserID(c), category, page, pageSize)
	if err != nil {
		response.InternalError(c, err.Error())
		return
	}
	response.Paginated(c, ss, total, page, pageSize)
}
func (h *AssetHandler) CreateScene(c *gin.Context) {
	var s model.ScenePreset
	if err := c.ShouldBindJSON(&s); err != nil {
		response.BadRequest(c, err.Error())
		return
	}
	uid := getUserID(c)
	s.OwnerID = &uid
	s.IsPreset = false
	if err := h.sceneSvc.Create(&s); err != nil {
		response.InternalError(c, err.Error())
		return
	}
	c.JSON(http.StatusCreated, s)
}
func (h *AssetHandler) ListProps(c *gin.Context) {
	category := c.DefaultQuery("category", "all")
	page, pageSize := response.GetPagination(c)
	ps, total, err := h.propSvc.List(getUserID(c), category, page, pageSize)
	if err != nil {
		response.InternalError(c, err.Error())
		return
	}
	response.Paginated(c, ps, total, page, pageSize)
}
func (h *AssetHandler) CreateProp(c *gin.Context) {
	var p model.PropPreset
	if err := c.ShouldBindJSON(&p); err != nil {
		response.BadRequest(c, err.Error())
		return
	}
	uid := getUserID(c)
	p.OwnerID = &uid
	p.IsPreset = false
	if err := h.propSvc.Create(&p); err != nil {
		response.InternalError(c, err.Error())
		return
	}
	c.JSON(http.StatusCreated, p)
}

func getUserID(c *gin.Context) uuid.UUID {
	return MustGetUserID(c)
}
