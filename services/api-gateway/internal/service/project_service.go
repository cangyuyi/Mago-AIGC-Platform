package service

import (
	"errors"
	"mago-agent/api-gateway/internal/model"
	"mago-agent/api-gateway/internal/repository"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type ProjectService struct {
	projectRepo *repository.ProjectRepository
}

func NewProjectService(projectRepo *repository.ProjectRepository) *ProjectService {
	return &ProjectService{projectRepo: projectRepo}
}

type CreateProjectInput struct {
	Name           string `json:"name" binding:"required"`
	Description    string `json:"description"`
	AspectRatio    string `json:"aspect_ratio"`
	TargetPlatform string `json:"target_platform"`
	TargetDuration int    `json:"target_duration"`
	Category       string `json:"category"`
}

func (s *ProjectService) Create(ownerID uuid.UUID, orgID *uuid.UUID, input *CreateProjectInput) (*model.Project, error) {
	project := &model.Project{
		BaseModel:      model.BaseModel{ID: uuid.New()},
		Name:           input.Name,
		Description:    input.Description,
		AspectRatio:    input.AspectRatio,
		TargetPlatform: input.TargetPlatform,
		TargetDuration: input.TargetDuration,
		Category:       input.Category,
		Status:         "draft",
		OwnerID:        ownerID,
		OrgID:          orgID,
		CurrentStep:    "ideation",
	}
	if project.AspectRatio == "" {
		project.AspectRatio = "9:16"
	}
	if err := s.projectRepo.Create(project); err != nil {
		return nil, err
	}
	return project, nil
}

func (s *ProjectService) GetByID(id uuid.UUID, userID uuid.UUID) (*model.Project, error) {
	project, err := s.projectRepo.FindByID(id)
	if err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, gorm.ErrRecordNotFound
		}
		return nil, err
	}
	if project.OwnerID != userID {
		return nil, repository.ErrAccessDenied
	}
	return project, nil
}

func (s *ProjectService) ListByOwner(ownerID uuid.UUID, page, pageSize int) ([]model.Project, int64, error) {
	return s.projectRepo.ListByOwner(ownerID, page, pageSize)
}

type UpdateProjectInput struct {
	Name        *string `json:"name"`
	Description *string `json:"description"`
	Status      *string `json:"status"`
	CurrentStep *string `json:"current_step"`
}

func (s *ProjectService) Update(id uuid.UUID, userID uuid.UUID, input *UpdateProjectInput) (*model.Project, error) {
	project, err := s.GetByID(id, userID)
	if err != nil {
		return nil, err
	}
	if input.Name != nil {
		project.Name = *input.Name
	}
	if input.Description != nil {
		project.Description = *input.Description
	}
	if input.Status != nil {
		project.Status = *input.Status
	}
	if input.CurrentStep != nil {
		project.CurrentStep = *input.CurrentStep
	}
	if err := s.projectRepo.Update(project); err != nil {
		return nil, err
	}
	return project, nil
}

func (s *ProjectService) Delete(id uuid.UUID, userID uuid.UUID) error {
	project, err := s.GetByID(id, userID)
	if err != nil {
		return err
	}
	return s.projectRepo.Delete(project.ID)
}
