package service

import (
	"github.com/google/uuid"
	"mago-agent/api-gateway/internal/model"
	"mago-agent/api-gateway/internal/repository"
)

type CharacterService struct {
	repo *repository.CharacterRepository
}

func NewCharacterService(repo *repository.CharacterRepository) *CharacterService {
	return &CharacterService{repo: repo}
}
func (s *CharacterService) Create(c *model.Character) error {
	if c.ID == uuid.Nil {
		c.ID = uuid.New()
	}
	return s.repo.Create(c)
}
func (s *CharacterService) GetByID(id uuid.UUID) (*model.Character, error) {
	return s.repo.FindByID(id)
}
func (s *CharacterService) GetByOwner(id, ownerID uuid.UUID) (*model.Character, error) {
	return s.repo.FindByOwner(id, ownerID)
}
func (s *CharacterService) ListByOwner(ownerID uuid.UUID, page, pageSize int) ([]model.Character, int64, error) {
	return s.repo.ListByOwner(ownerID, page, pageSize)
}
func (s *CharacterService) Update(c *model.Character) error { return s.repo.Update(c) }
func (s *CharacterService) UpdateOwned(c *model.Character, ownerID uuid.UUID) error {
	return s.repo.UpdateOwned(c, ownerID)
}
func (s *CharacterService) Delete(id uuid.UUID) error { return s.repo.Delete(id, uuid.Nil) }
func (s *CharacterService) DeleteOwned(id, ownerID uuid.UUID) error {
	return s.repo.Delete(id, ownerID)
}
func (s *CharacterService) AddImage(img *model.CharacterRefImage) error { return s.repo.AddImage(img) }
func (s *CharacterService) ListImages(charID uuid.UUID) ([]model.CharacterRefImage, error) {
	return s.repo.ListImages(charID)
}
func (s *CharacterService) DeleteImage(id uuid.UUID) error { return s.repo.DeleteImage(id) }
func (s *CharacterService) DeleteImageOwned(id, ownerID uuid.UUID) error {
	return s.repo.DeleteImageOwned(id, ownerID)
}

type StyleService struct{ repo *repository.StyleRepository }

func NewStyleService(repo *repository.StyleRepository) *StyleService {
	return &StyleService{repo: repo}
}
func (s *StyleService) Create(p *model.StylePreset) error {
	if p.ID == uuid.Nil {
		p.ID = uuid.New()
	}
	return s.repo.Create(p)
}
func (s *StyleService) GetByID(id uuid.UUID) (*model.StylePreset, error) { return s.repo.FindByID(id) }
func (s *StyleService) GetVisibleByOwner(id, ownerID uuid.UUID) (*model.StylePreset, error) {
	return s.repo.FindVisibleByOwner(id, ownerID)
}
func (s *StyleService) List(ownerID uuid.UUID, category string, page, pageSize int) ([]model.StylePreset, int64, error) {
	return s.repo.ListByOwnerOrPreset(ownerID, category, page, pageSize)
}
func (s *StyleService) Update(p *model.StylePreset) error { return s.repo.Update(p) }
func (s *StyleService) UpdateOwned(p *model.StylePreset, ownerID uuid.UUID) error {
	return s.repo.UpdateOwned(p, ownerID)
}
func (s *StyleService) Delete(id uuid.UUID) error { return s.repo.Delete(id) }
func (s *StyleService) DeleteOwned(id, ownerID uuid.UUID) error {
	return s.repo.DeleteOwned(id, ownerID)
}
func (s *StyleService) Categories(ownerID uuid.UUID) ([]string, error) {
	return s.repo.ListCategories(ownerID)
}

type SceneService struct{ repo *repository.SceneRepository }

func NewSceneService(repo *repository.SceneRepository) *SceneService {
	return &SceneService{repo: repo}
}
func (s *SceneService) Create(sc *model.ScenePreset) error {
	if sc.ID == uuid.Nil {
		sc.ID = uuid.New()
	}
	return s.repo.Create(sc)
}
func (s *SceneService) GetByID(id uuid.UUID) (*model.ScenePreset, error) { return s.repo.FindByID(id) }
func (s *SceneService) List(ownerID uuid.UUID, category string, page, pageSize int) ([]model.ScenePreset, int64, error) {
	return s.repo.List(ownerID, category, page, pageSize)
}
func (s *SceneService) Update(sc *model.ScenePreset) error { return s.repo.Update(sc) }
func (s *SceneService) Delete(id uuid.UUID) error          { return s.repo.Delete(id) }

type PropService struct{ repo *repository.PropRepository }

func NewPropService(repo *repository.PropRepository) *PropService { return &PropService{repo: repo} }
func (s *PropService) Create(p *model.PropPreset) error {
	if p.ID == uuid.Nil {
		p.ID = uuid.New()
	}
	return s.repo.Create(p)
}
func (s *PropService) GetByID(id uuid.UUID) (*model.PropPreset, error) { return s.repo.FindByID(id) }
func (s *PropService) List(ownerID uuid.UUID, category string, page, pageSize int) ([]model.PropPreset, int64, error) {
	return s.repo.List(ownerID, category, page, pageSize)
}
func (s *PropService) Update(p *model.PropPreset) error { return s.repo.Update(p) }
func (s *PropService) Delete(id uuid.UUID) error        { return s.repo.Delete(id) }
