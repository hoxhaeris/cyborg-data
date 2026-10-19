package orgdatacore

import "time"

//go:generate make generate

// The on-disk comprehensive-index types are generated from the canonical
// orgindex-schema contract into index_gen.go (regenerate with `make generate`).
// The aliases below re-export the generated models under the historical
// orgdatacore names so callers and method signatures stay unchanged.
//
// All five hierarchy collections (teams / orgs / pillars / team_groups /
// cohorts) are structurally identical, so they share the single canonical
// HierarchyEntity. Because Team/Org/Pillar/TeamGroup are aliases to one type, a
// Go type switch cannot tell them apart (see parity/go_runner).
type (
	Data      = ComprehensiveIndexModel
	Employee  = EmployeeEntry
	Component = ComponentEntry
	Group     = GroupInfo
	GroupType = GroupTypeInfo

	Team      = HierarchyEntity
	Org       = HierarchyEntity
	Pillar    = HierarchyEntity
	TeamGroup = HierarchyEntity

	ParentInfo  = ParentRef
	SlackConfig = SlackConfigInfo
	ChannelInfo = SlackChannelInfo
	AliasInfo   = SlackAliasInfo

	MembershipInfo  = MembershipEntry
	MembershipIndex = MembershipIndexInfo

	JiraOwnerInfo      = JiraOwner
	ComponentOwnerInfo = ComponentOwner
)

// ----------------------------------------------------------------------------
// Query-result and infrastructure types.
//
// These are computed at query time or used internally; they are not part of the
// on-disk index contract, so they stay hand-written and are not generated.
// ----------------------------------------------------------------------------

// ComponentOwnership represents a component owned by a team, with ownership types
type ComponentOwnership struct {
	Component      string   `json:"component"`
	OwnershipTypes []string `json:"ownership_types"`
}

// HierarchyPathEntry represents a single entry in a hierarchy path
type HierarchyPathEntry struct {
	Name     string `json:"name"`
	Type     string `json:"type"`
	StableID string `json:"stable_id,omitempty"`
}

// HierarchyNode represents a node in the descendants tree with nested children
type HierarchyNode struct {
	Name     string          `json:"name"`
	Type     string          `json:"type"`
	StableID string          `json:"stable_id,omitempty"`
	Children []HierarchyNode `json:"children"`
}

// JiraOwnership represents a project/component ownership entry
type JiraOwnership struct {
	Project   string `json:"project"`
	Component string `json:"component"`
}

// DataVersion tracks the version of loaded data for hot reload
type DataVersion struct {
	LoadTime      time.Time
	ConfigMaps    map[string]string // ConfigMap name -> checksum/version
	OrgCount      int
	EmployeeCount int
}
