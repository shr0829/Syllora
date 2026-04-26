import React from "react";

export default function TrackTabs({ tracks, activeTrackId, onSelect }) {
  return (
    <nav className="track-tabs" aria-label="学习轨选择">
      {tracks.map((track) => {
        const isActive = track.id === activeTrackId;

        return (
          <button
            key={track.id}
            type="button"
            className={isActive ? "track-tab is-active" : "track-tab"}
            onClick={() => onSelect(track.id)}
          >
            <span className="track-tab-label">{track.label}</span>
            <strong>{track.title}</strong>
            <span>{track.level}</span>
          </button>
        );
      })}
    </nav>
  );
}
