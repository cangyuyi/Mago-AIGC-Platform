package service

import (
	"errors"
	"fmt"
	"time"

	"github.com/google/uuid"
	"mago-agent/api-gateway/internal/model"
	"mago-agent/api-gateway/internal/repository"
)

// ScriptService handles script and storyboard business logic.
type ScriptService struct {
	repo        *repository.ScriptRepository
	sbRepo      *repository.StoryboardRepository
	projectRepo *repository.ProjectRepository
}

// NewScriptService creates a service that verifies every resource through its owning project.
func NewScriptService(repo *repository.ScriptRepository, sbRepo *repository.StoryboardRepository, projectRepo *repository.ProjectRepository) *ScriptService {
	return &ScriptService{repo: repo, sbRepo: sbRepo, projectRepo: projectRepo}
}

func (s *ScriptService) checkProjectOwner(projectID, userID uuid.UUID) error {
	project, err := s.projectRepo.FindByID(projectID)
	if err != nil {
		return err
	}
	if project.OwnerID != userID {
		return repository.ErrAccessDenied
	}
	return nil
}

func (s *ScriptService) Create(script *model.Script) error { return s.repo.Create(script) }
func (s *ScriptService) CreateOwned(script *model.Script, userID uuid.UUID) error {
	if err := s.checkProjectOwner(script.ProjectID, userID); err != nil {
		return err
	}
	if script.ID == uuid.Nil {
		script.ID = uuid.New()
	}
	return s.repo.Create(script)
}
func (s *ScriptService) GetByID(id uuid.UUID) (*model.Script, error) { return s.repo.FindByID(id) }
func (s *ScriptService) GetByIDOwned(id, userID uuid.UUID) (*model.Script, error) {
	script, err := s.repo.FindByID(id)
	if err != nil {
		return nil, err
	}
	if err := s.checkProjectOwner(script.ProjectID, userID); err != nil {
		return nil, err
	}
	return script, nil
}
func (s *ScriptService) ListByProject(projectID uuid.UUID) ([]model.Script, error) {
	return s.repo.ListByProject(projectID)
}
func (s *ScriptService) ListByProjectOwned(projectID, userID uuid.UUID) ([]model.Script, error) {
	if err := s.checkProjectOwner(projectID, userID); err != nil {
		return nil, err
	}
	return s.repo.ListByProject(projectID)
}
func (s *ScriptService) Update(script *model.Script) error { return s.repo.Update(script) }
func (s *ScriptService) UpdateOwned(script *model.Script, userID uuid.UUID) error {
	current, err := s.GetByIDOwned(script.ID, userID)
	if err != nil {
		return err
	}
	script.ProjectID = current.ProjectID
	return s.repo.UpdateOwned(script)
}
func (s *ScriptService) Delete(id uuid.UUID) error { return s.repo.Delete(id) }
func (s *ScriptService) DeleteOwned(id, userID uuid.UUID) error {
	if _, err := s.GetByIDOwned(id, userID); err != nil {
		return err
	}
	return s.repo.Delete(id)
}

func (s *ScriptService) CreateStoryboard(sb *model.Storyboard) error { return s.sbRepo.Create(sb) }
func (s *ScriptService) CreateStoryboardOwned(sb *model.Storyboard, userID uuid.UUID) error {
	if err := s.checkProjectOwner(sb.ProjectID, userID); err != nil {
		return err
	}
	script, err := s.repo.FindByID(sb.ScriptID)
	if err != nil {
		return err
	}
	if script.ProjectID != sb.ProjectID {
		return repository.ErrAccessDenied
	}
	if sb.ID == uuid.Nil {
		sb.ID = uuid.New()
	}
	return s.sbRepo.Create(sb)
}
func (s *ScriptService) GetStoryboard(id uuid.UUID) (*model.Storyboard, error) {
	return s.sbRepo.FindByID(id)
}
func (s *ScriptService) GetStoryboardOwned(id, userID uuid.UUID) (*model.Storyboard, error) {
	sb, err := s.sbRepo.FindByID(id)
	if err != nil {
		return nil, err
	}
	if err := s.checkProjectOwner(sb.ProjectID, userID); err != nil {
		return nil, err
	}
	return sb, nil
}
func (s *ScriptService) GetStoryboardShots(storyboardID uuid.UUID) ([]model.StoryboardShot, error) {
	return s.sbRepo.GetShots(storyboardID)
}
func (s *ScriptService) GetStoryboardShotsOwned(storyboardID, userID uuid.UUID) ([]model.StoryboardShot, error) {
	if _, err := s.GetStoryboardOwned(storyboardID, userID); err != nil {
		return nil, err
	}
	return s.sbRepo.GetShots(storyboardID)
}
func (s *ScriptService) ListStoryboardsByProject(projectID uuid.UUID) ([]model.Storyboard, error) {
	return s.sbRepo.ListByProject(projectID)
}
func (s *ScriptService) ListStoryboardsByProjectOwned(projectID, userID uuid.UUID) ([]model.Storyboard, error) {
	if err := s.checkProjectOwner(projectID, userID); err != nil {
		return nil, err
	}
	return s.sbRepo.ListByProject(projectID)
}
func (s *ScriptService) CreateShot(shot *model.StoryboardShot) error {
	return s.sbRepo.CreateShot(shot)
}
func (s *ScriptService) UpdateShot(shot *model.StoryboardShot) error {
	return s.sbRepo.UpdateShot(shot)
}
func (s *ScriptService) DeleteShot(id uuid.UUID) error { return s.sbRepo.DeleteShot(id) }

// MaxShotsPerStoryboard guards against unbounded payloads being stored.
const MaxShotsPerStoryboard = 500

var (
	// ErrNoShots is returned when a replace request carries an empty shot list.
	ErrNoShots = errors.New("at least one shot is required")
	// ErrTooManyShots is returned when the shot list exceeds the hard limit.
	ErrTooManyShots = errors.New("too many shots")
)

// NormalizeShots makes a client supplied shot list safe to persist: the parent
// storyboard id is always taken from the path, ids are generated, indexes are
// renumbered from 1 so the reading order can never be corrupted, and every
// duration must be a positive number of seconds.
func NormalizeShots(storyboardID uuid.UUID, in []model.StoryboardShot) ([]model.StoryboardShot, error) {
	if len(in) == 0 {
		return nil, ErrNoShots
	}
	if len(in) > MaxShotsPerStoryboard {
		return nil, fmt.Errorf("%w: max %d", ErrTooManyShots, MaxShotsPerStoryboard)
	}
	out := make([]model.StoryboardShot, 0, len(in))
	for i := range in {
		shot := in[i]
		if shot.Duration <= 0 {
			return nil, fmt.Errorf("shot %d: duration must be greater than 0", i+1)
		}
		shot.ID = uuid.New()
		shot.StoryboardID = storyboardID
		shot.ShotIndex = i + 1
		shot.CreatedAt = time.Time{}
		shot.UpdatedAt = time.Time{}
		out = append(out, shot)
	}
	return out, nil
}

// ReplaceShotsOwned overwrites the shot list of a storyboard the user owns.
func (s *ScriptService) ReplaceShotsOwned(storyboardID, userID uuid.UUID, in []model.StoryboardShot) ([]model.StoryboardShot, error) {
	sb, err := s.GetStoryboardOwned(storyboardID, userID)
	if err != nil {
		return nil, err
	}
	shots, err := NormalizeShots(sb.ID, in)
	if err != nil {
		return nil, err
	}
	return s.sbRepo.ReplaceShots(sb.ID, shots)
}
