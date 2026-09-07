"""Policies for placement and task offloading."""

from .offloading import (
	FixedServerPolicy,
	HybridHeuristicPolicy,
	LeastLoadedPolicy,
	NearestServerPolicy,
	OffloadingPolicy,
	RandomPolicy,
)

__all__ = [
	"FixedServerPolicy",
	"HybridHeuristicPolicy",
	"LeastLoadedPolicy",
	"NearestServerPolicy",
	"OffloadingPolicy",
	"RandomPolicy",
]
