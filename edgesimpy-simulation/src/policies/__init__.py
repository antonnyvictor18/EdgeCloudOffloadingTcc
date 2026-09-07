"""Policies for placement and task offloading."""

from .offloading import (
	FixedServerPolicy,
	NearestServerPolicy,
	OffloadingPolicy,
	RandomPolicy,
)

__all__ = [
	"FixedServerPolicy",
	"NearestServerPolicy",
	"OffloadingPolicy",
	"RandomPolicy",
]
