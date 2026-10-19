package orgdatacore

import (
	"testing"
)

func TestGetTeamGroupByName(t *testing.T) {
	service := NewService()
	service.data = &Data{
		Lookups: &Lookups{
			TeamGroups: map[string]TeamGroup{
				"Platform Teams": {
					StableID: "tg1",
					Name:     "Platform Teams",
					Group: &Group{
						Type: &GroupType{
							Name: "team_group",
						},
						ResolvedPeopleUIDList: []string{"user1", "user2"},
					},
				},
			},
		},
	}

	tests := []struct {
		name             string
		teamGroupName    string
		expectNil        bool
		expectedStableID string
	}{
		{
			name:             "existing team group",
			teamGroupName:    "Platform Teams",
			expectNil:        false,
			expectedStableID: "tg1",
		},
		{
			name:          "nonexistent team group",
			teamGroupName: "Nonexistent",
			expectNil:     true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := service.GetTeamGroupByName(tt.teamGroupName)
			if tt.expectNil {
				if result != nil {
					t.Errorf("expected nil, got %+v", result)
				}
			} else {
				if result == nil {
					t.Errorf("expected team group, got nil")
				} else if result.StableID != tt.expectedStableID {
					t.Errorf("expected StableID %s, got %s", tt.expectedStableID, result.StableID)
				}
			}
		})
	}
}

func TestGetAllTeamGroupNames(t *testing.T) {
	service := NewService()
	service.data = &Data{
		Lookups: &Lookups{
			TeamGroups: map[string]TeamGroup{
				"Platform Teams": {
					StableID: "tg1",
					Name:     "Platform Teams",
				},
				"Product Teams": {
					StableID: "tg2",
					Name:     "Product Teams",
				},
			},
		},
	}

	names := service.GetAllTeamGroupNames()
	if len(names) != 2 {
		t.Errorf("expected 2 team group names, got %d", len(names))
	}

	// Check both names are present (order doesn't matter)
	found := make(map[string]bool)
	for _, name := range names {
		found[name] = true
	}

	if !found["Platform Teams"] || !found["Product Teams"] {
		t.Errorf("expected to find Platform Teams and Product Teams, got %v", names)
	}
}
