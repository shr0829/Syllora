import React from "react";

import SpotlightCard from "./reactbits/SpotlightCard";

export default function StageDeck({
  stages,
  completedStageIds,
  activeStageId,
  onSelectStage,
  onToggleStage,
}) {
  return (
    <div className="stage-deck">
      {stages.map((stage) => {
        const isComplete = completedStageIds.includes(stage.id);
        const isActive = activeStageId === stage.id;

        return (
          <SpotlightCard
            key={stage.id}
            className={isActive ? "stage-card stage-card-active" : "stage-card"}
            spotlightColor="rgba(249, 115, 22, 0.18)"
          >
            <button
              type="button"
              className="stage-open-button"
              onClick={() => onSelectStage(stage.id)}
            >
              <span className="stage-card-title">{stage.title}</span>
              <span className="stage-card-summary">{stage.summary}</span>
            </button>

            <label className="stage-check">
              <input
                type="checkbox"
                checked={isComplete}
                onChange={() => onToggleStage(stage.id)}
              />
              <span>{isComplete ? "已完成" : "标记完成"}</span>
            </label>
          </SpotlightCard>
        );
      })}
    </div>
  );
}
