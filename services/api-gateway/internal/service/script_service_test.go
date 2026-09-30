package service

import (
	"errors"
	"testing"

	"github.com/google/uuid"
	"mago-agent/api-gateway/internal/model"
)

func TestNormalizeShotsRejectsEmptyList(t *testing.T) {
	if _, err := NormalizeShots(uuid.New(), nil); !errors.Is(err, ErrNoShots) {
		t.Fatalf("err = %v, want ErrNoShots", err)
	}
}

func TestNormalizeShotsRejectsNonPositiveDuration(t *testing.T) {
	in := []model.StoryboardShot{{Duration: 3}, {Duration: 0}}
	if _, err := NormalizeShots(uuid.New(), in); err == nil {
		t.Fatal("expected an error for a zero duration shot")
	}
}

func TestNormalizeShotsRewritesIdentityAndOrder(t *testing.T) {
	parent := uuid.New()
	stranger := uuid.New()
	in := []model.StoryboardShot{
		{BaseModel: model.BaseModel{ID: stranger}, StoryboardID: stranger, ShotIndex: 42, Duration: 2.5, SubjectDescription: "a"},
		{ShotIndex: 7, Duration: 1.5, SubjectDescription: "b"},
	}

	out, err := NormalizeShots(parent, in)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(out) != 2 {
		t.Fatalf("len = %d, want 2", len(out))
	}
	for i, shot := range out {
		if shot.ShotIndex != i+1 {
			t.Errorf("shot %d index = %d, want %d", i, shot.ShotIndex, i+1)
		}
		if shot.StoryboardID != parent {
			t.Errorf("shot %d keeps a client supplied storyboard id", i)
		}
		if shot.ID == uuid.Nil || shot.ID == stranger {
			t.Errorf("shot %d was not assigned a fresh id", i)
		}
	}
	if out[0].SubjectDescription != "a" || out[1].Duration != 1.5 {
		t.Error("normalizing must not drop content fields")
	}
	// The caller slice must stay untouched so a failed retry keeps its data.
	if in[0].ShotIndex != 42 {
		t.Error("NormalizeShots mutated the input slice")
	}
}

func TestNormalizeShotsEnforcesHardLimit(t *testing.T) {
	in := make([]model.StoryboardShot, MaxShotsPerStoryboard+1)
	for i := range in {
		in[i] = model.StoryboardShot{Duration: 1}
	}
	if _, err := NormalizeShots(uuid.New(), in); !errors.Is(err, ErrTooManyShots) {
		t.Fatalf("err = %v, want ErrTooManyShots", err)
	}
}
