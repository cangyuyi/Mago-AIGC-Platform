package repository

import (
	"github.com/google/uuid"
	"gorm.io/gorm"
	"mago-agent/api-gateway/internal/model"
)

type CharacterRepository struct{ db *gorm.DB }

func NewCharacterRepository(db *gorm.DB) *CharacterRepository { return &CharacterRepository{db: db} }

func (r *CharacterRepository) Create(c *model.Character) error { return r.db.Create(c).Error }
func (r *CharacterRepository) FindByID(id uuid.UUID) (*model.Character, error) {
	var c model.Character
	if err := r.db.Where("id = ?", id).First(&c).Error; err != nil {
		return nil, err
	}
	return &c, nil
}
func (r *CharacterRepository) FindByOwner(id, ownerID uuid.UUID) (*model.Character, error) {
	var c model.Character
	if err := r.db.Where("id = ? AND owner_id = ?", id, ownerID).First(&c).Error; err != nil {
		return nil, err
	}
	return &c, nil
}
func (r *CharacterRepository) ListByOwner(ownerID uuid.UUID, page, pageSize int) ([]model.Character, int64, error) {
	var cs []model.Character
	var total int64
	q := r.db.Where("owner_id = ?", ownerID)
	if err := q.Model(&model.Character{}).Count(&total).Error; err != nil {
		return nil, 0, err
	}
	if err := q.Order("updated_at DESC").Offset((page - 1) * pageSize).Limit(pageSize).Find(&cs).Error; err != nil {
		return nil, 0, err
	}
	return cs, total, nil
}
func (r *CharacterRepository) Update(c *model.Character) error { return r.db.Save(c).Error }
func (r *CharacterRepository) UpdateOwned(c *model.Character, ownerID uuid.UUID) error {
	result := r.db.Model(&model.Character{}).
		Where("id = ? AND owner_id = ? AND is_preset = false", c.ID, ownerID).
		Updates(map[string]interface{}{
			"visibility":           c.Visibility,
			"name":                 c.Name,
			"description":          c.Description,
			"gender":               c.Gender,
			"age_appearance":       c.AgeAppearance,
			"ethnicity":            c.Ethnicity,
			"face_desc":            c.FaceDesc,
			"hair_desc":            c.HairDesc,
			"body_desc":            c.BodyDesc,
			"clothing_default":     c.ClothingDefault,
			"skin_details":         c.SkinDetails,
			"distinctive_features": c.DistinctiveFeatures,
			"personality_vibe":     c.PersonalityVibe,
			"face_id_weight":       c.FaceIDWeight,
			"ip_adapter_scale":     c.IPAdapterScale,
			"reference_strategy":   c.RefStrategy,
			"seed_base":            c.SeedBase,
			"model_compat":         c.ModelCompat,
			"prompt_fragment":      c.PromptFragment,
			"negative_frag":        c.NegativeFrag,
			"tags":                 c.Tags,
		})
	if result.Error != nil {
		return result.Error
	}
	if result.RowsAffected == 0 {
		return gorm.ErrRecordNotFound
	}
	return nil
}
func (r *CharacterRepository) Delete(id, ownerID uuid.UUID) error {
	result := r.db.Where("id = ? AND owner_id = ?", id, ownerID).Delete(&model.Character{})
	if result.Error != nil {
		return result.Error
	}
	if result.RowsAffected == 0 {
		return gorm.ErrRecordNotFound
	}
	return nil
}
func (r *CharacterRepository) AddImage(img *model.CharacterRefImage) error {
	return r.db.Create(img).Error
}
func (r *CharacterRepository) ListImages(charID uuid.UUID) ([]model.CharacterRefImage, error) {
	var imgs []model.CharacterRefImage
	err := r.db.Where("character_id = ?", charID).Order("sort_order ASC").Find(&imgs).Error
	return imgs, err
}
func (r *CharacterRepository) DeleteImage(id uuid.UUID) error {
	return r.db.Delete(&model.CharacterRefImage{}, "id = ?", id).Error
}

func (r *CharacterRepository) DeleteImageOwned(id, ownerID uuid.UUID) error {
	result := r.db.Exec(`DELETE FROM character_ref_images
		WHERE id = ? AND character_id IN (SELECT id FROM characters WHERE owner_id = ?)`, id, ownerID)
	if result.Error != nil {
		return result.Error
	}
	if result.RowsAffected == 0 {
		return gorm.ErrRecordNotFound
	}
	return nil
}
