package ai.mordecai.shell

import android.service.quicksettings.Tile
import android.service.quicksettings.TileService

class MordecaiTileService : TileService() {
    override fun onStartListening() {
        super.onStartListening()
        qsTile?.state = Tile.STATE_ACTIVE
        qsTile?.label = getString(R.string.tile_label)
        qsTile?.updateTile()
    }

    override fun onClick() {
        super.onClick()
        MordecaiShellService.start(this, MordecaiShellService.ACTION_VOICE_COMMAND)
    }
}