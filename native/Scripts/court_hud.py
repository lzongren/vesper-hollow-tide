"""A screen-space health display for the possessed swordswoman and active court."""

from pathlib import Path
import unreal

from court_encounter import live


def anchors(x, y):
    point = unreal.Vector2D(x, y)
    return unreal.Anchors(minimum=point, maximum=point)


class LifeRail:
    def __init__(self, hud, kind, origin, anchor, width, height, inset, capacity):
        self.panel = unreal.new_object(unreal.CanvasPanel, outer=hud.root)
        slot = hud.root.add_child_to_canvas(self.panel)
        slot.set_anchors(anchor)
        slot.set_position(unreal.Vector2D(*origin))
        slot.set_size(unreal.Vector2D(width, height))
        self.capacity = capacity
        self.last = None
        self.trail = None
        self.hold_until = 0

        def image(name, x, y, w, h):
            widget = unreal.new_object(unreal.Image, outer=self.panel)
            widget.set_brush_from_texture(hud.textures[name])
            child = self.panel.add_child_to_canvas(widget)
            child.set_position(unreal.Vector2D(x, y))
            child.set_size(unreal.Vector2D(w, h))
            return widget, child

        image(kind + "-rail", 0, 0, width, height)
        _, self.trail_slot = image("damage", inset, (height - 8) / 2, capacity, 8)
        _, self.fill_slot = image(
            kind + "-lacquer", inset, (height - 8) / 2, capacity, 8
        )
        if kind == "boss":
            self.title, _ = image("Bellwarden", (width - 320) / 2, -36, 320, 42)

    def update(self, fraction, now, dt):
        if self.last is None or fraction > self.last:
            self.trail = fraction
            self.trail_slot.set_size(unreal.Vector2D(self.capacity * fraction, 8))
        elif fraction < self.last:
            self.hold_until = now + 0.26
        if self.last != fraction:
            self.fill_slot.set_size(unreal.Vector2D(self.capacity * fraction, 8))
            self.last = fraction
        if self.trail > fraction and now >= self.hold_until:
            self.trail = max(fraction, self.trail - dt * 0.8)
            self.trail_slot.set_size(unreal.Vector2D(self.capacity * self.trail, 8))


def health(actor):
    maximum = actor.get_editor_property("Max HP")
    value = actor.get_editor_property("Current HP")
    return min(1, max(0, value / maximum)) if maximum > 0 else 0


class CourtHUD:
    def __init__(self):
        self.root = self.pawn = self.current = None
        self.textures = {}
        self.seen = set()
        self.victory_until = None

    def clear(self):
        if live(self.root):
            self.viewport.remove_widget(self.root)
        self.root = self.pawn = self.current = None
        self.player = self.boss = None
        self.seen.clear()
        self.victory_until = None
        self.textures.clear()

    def mount(self, pawn):
        self.clear()
        # Standalone -game is owned by GameEngine. The Python editor helper
        # resolves GEditor and cannot see this engine's subsystem.
        self.viewport = next(
            (
                sub
                for sub in unreal.ObjectIterator(unreal.GameViewportSubsystem)
                if sub.get_outer().get_class().get_name() == "GameEngine"
            ),
            None,
        )
        if self.viewport is None:
            return
        folder = (
            Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
            / "Art/Lifebars"
        )
        for name in (
            "player-rail",
            "player-lacquer",
            "boss-rail",
            "boss-lacquer",
            "Bellwarden",
            "damage",
            "VeiledHeron",
            "CinderSaint",
        ):
            tex = unreal.RenderingLibrary.import_file_as_texture2d(
                pawn, str(folder / (name + ".png"))
            )
            if tex is None:
                raise RuntimeError("Missing HUD texture " + name)
            self.textures[name] = tex
        self.root = unreal.new_object(unreal.CanvasPanel, outer=pawn)
        self.root.set_visibility(unreal.SlateVisibility.HIT_TEST_INVISIBLE)
        self.player = LifeRail(
            self, "player", (28, 24), anchors(0, 0), 266, 42, 39, 218
        )
        self.boss = LifeRail(
            self, "boss", (-320, -66), anchors(0.5, 1), 640, 32, 16, 608
        )
        self.boss.panel.set_visibility(unreal.SlateVisibility.COLLAPSED)
        if not self.viewport.add_widget(
            self.root, unreal.GameViewportWidgetSlot(z_order=2)
        ):
            raise RuntimeError("Could not mount combat HUD")
        self.pawn = pawn
        unreal.log("VESPER_COURT_HUD_ACTIVE")

    def hide_template_bar(self, actor):
        if actor in self.seen:
            return
        for component in actor.get_components_by_class(unreal.WidgetComponent):
            widget = component.get_user_widget_object()
            if widget and widget.get_class().get_name() == "UI_LifeBar_C":
                component.set_visibility(False)
        self.seen.add(actor)

    def update(self, pawn, duels, dt):
        if self.pawn != pawn:
            self.mount(pawn)
            if self.pawn is None:
                return
        self.hide_template_bar(pawn)
        now = unreal.GameplayStatics.get_time_seconds(pawn)
        self.player.update(health(pawn), now, dt)
        target = None
        for duel in duels:
            if live(duel.actor):
                self.hide_template_bar(duel.actor)
                if duel.state not in ("waiting", "defeated"):
                    target = duel
        if target is None and self.current and self.current.state == "defeated":
            if self.victory_until is None:
                self.victory_until = now + 1
            if now < self.victory_until:
                self.boss.update(0, now, dt)
                self.boss.panel.set_render_opacity(
                    min(1, (self.victory_until - now) / 0.45)
                )
                return
        if target is not self.current:
            self.current = target
            self.victory_until = None
            if target is None:
                self.boss.panel.set_visibility(unreal.SlateVisibility.COLLAPSED)
            else:
                self.boss.last = None
                self.boss.panel.set_render_opacity(1)
                self.boss.title.set_brush_from_texture(self.textures[target.tag])
                self.boss.panel.set_visibility(
                    unreal.SlateVisibility.HIT_TEST_INVISIBLE
                )
        if target:
            self.boss.update(health(target.actor), now, dt)
