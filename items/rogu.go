package items

// TODO Update rogu self

func roguItem() Item {
	return Item{
		Name:        "rogu",
		Priority:    -1,
		Type:        ScriptItem,
		IsInstalled: func() (bool, error) { return true, nil },
		//Install:     roguInstall,
		//Uninstall:   roguUninstall,
		//Update:      roguUpdate,
	}
}
