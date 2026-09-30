package service

import (
	"github.com/google/uuid"
	"mago-agent/api-gateway/internal/model"
	"mago-agent/api-gateway/internal/repository"
)

type PromptService struct {
	repo        *repository.PromptRepository
	projectRepo *repository.ProjectRepository
	sbRepo      *repository.StoryboardRepository
}

// NewPromptService keeps the storyboard repository optional for source compatibility
// with older integrations. Owned package creation/addition requires it so that
// cross-project storyboard and shot references cannot be introduced.
func NewPromptService(repo *repository.PromptRepository, projectRepo *repository.ProjectRepository, sbRepos ...*repository.StoryboardRepository) *PromptService {
	var sbRepo *repository.StoryboardRepository
	if len(sbRepos) > 0 {
		sbRepo = sbRepos[0]
	}
	return &PromptService{repo: repo, projectRepo: projectRepo, sbRepo: sbRepo}
}

func (s *PromptService) ownsProject(projectID, userID uuid.UUID) error {
	project, err := s.projectRepo.FindByID(projectID)
	if err != nil {
		return err
	}
	if project.OwnerID != userID {
		return repository.ErrAccessDenied
	}
	return nil
}

func (s *PromptService) CreatePackage(p *model.PromptPackage) error {
	if p.ID == uuid.Nil {
		p.ID = uuid.New()
	}
	return s.repo.CreatePackage(p)
}
func (s *PromptService) CreatePackageOwned(p *model.PromptPackage, userID uuid.UUID) error {
	if err := s.ownsProject(p.ProjectID, userID); err != nil {
		return err
	}
	if s.sbRepo == nil {
		return repository.ErrAccessDenied
	}
	storyboard, err := s.sbRepo.FindByID(p.StoryboardID)
	if err != nil {
		return err
	}
	if storyboard.ProjectID != p.ProjectID {
		return repository.ErrAccessDenied
	}
	return s.CreatePackage(p)
}
func (s *PromptService) GetPackage(id uuid.UUID) (*model.PromptPackage, error) {
	return s.repo.GetPackage(id)
}
func (s *PromptService) GetPackageOwned(id, userID uuid.UUID) (*model.PromptPackage, error) {
	p, err := s.repo.GetPackage(id)
	if err != nil {
		return nil, err
	}
	if err := s.ownsProject(p.ProjectID, userID); err != nil {
		return nil, err
	}
	return p, nil
}
func (s *PromptService) ListPackages(projectID uuid.UUID) ([]model.PromptPackage, error) {
	return s.repo.ListPackages(projectID)
}
func (s *PromptService) ListPackagesOwned(projectID, userID uuid.UUID) ([]model.PromptPackage, error) {
	if err := s.ownsProject(projectID, userID); err != nil {
		return nil, err
	}
	return s.repo.ListPackages(projectID)
}
func (s *PromptService) CreatePrompts(ps []model.Prompt) error { return s.repo.CreatePrompts(ps) }
func (s *PromptService) CreatePromptsOwned(packageID, userID uuid.UUID, ps []model.Prompt) error {
	pkg, err := s.GetPackageOwned(packageID, userID)
	if err != nil {
		return err
	}
	if s.sbRepo == nil {
		return repository.ErrAccessDenied
	}
	shots, err := s.sbRepo.GetShots(pkg.StoryboardID)
	if err != nil {
		return err
	}
	allowedShotIDs := make(map[uuid.UUID]struct{}, len(shots))
	for _, shot := range shots {
		allowedShotIDs[shot.ID] = struct{}{}
	}
	for i := range ps {
		if _, ok := allowedShotIDs[ps[i].ShotID]; !ok {
			return repository.ErrAccessDenied
		}
		if ps[i].ID == uuid.Nil {
			ps[i].ID = uuid.New()
		}
		ps[i].PackageID = packageID
	}
	return s.repo.CreatePrompts(ps)
}
func (s *PromptService) ListPrompts(packageID uuid.UUID) ([]model.Prompt, error) {
	return s.repo.ListPrompts(packageID)
}
func (s *PromptService) ListPromptsOwned(packageID, userID uuid.UUID) ([]model.Prompt, error) {
	if _, err := s.GetPackageOwned(packageID, userID); err != nil {
		return nil, err
	}
	return s.repo.ListPrompts(packageID)
}
func (s *PromptService) UpdatePrompt(p *model.Prompt) error { return s.repo.UpdatePrompt(p) }
func (s *PromptService) DeletePackage(id uuid.UUID) error   { return s.repo.DeletePackage(id) }
func (s *PromptService) DeletePackageOwned(id, userID uuid.UUID) error {
	if _, err := s.GetPackageOwned(id, userID); err != nil {
		return err
	}
	return s.repo.DeletePackage(id)
}
