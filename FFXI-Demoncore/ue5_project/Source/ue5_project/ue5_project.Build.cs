// Copyright Epic Games, Inc. All Rights Reserved.

using UnrealBuildTool;

public class ue5_project : ModuleRules
{
	public ue5_project(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(new string[] {
			"Core",
			"CoreUObject",
			"Engine",
			"InputCore",
			"EnhancedInput",
			"AIModule",
			"StateTreeModule",
			"GameplayStateTreeModule",
			"UMG",
			"Slate"
		});

		PrivateDependencyModuleNames.AddRange(new string[] { });

		PublicIncludePaths.AddRange(new string[] {
			"ue5_project",
			"ue5_project/Variant_Platforming",
			"ue5_project/Variant_Platforming/Animation",
			"ue5_project/Variant_Combat",
			"ue5_project/Variant_Combat/AI",
			"ue5_project/Variant_Combat/Animation",
			"ue5_project/Variant_Combat/Gameplay",
			"ue5_project/Variant_Combat/Interfaces",
			"ue5_project/Variant_Combat/UI",
			"ue5_project/Variant_SideScrolling",
			"ue5_project/Variant_SideScrolling/AI",
			"ue5_project/Variant_SideScrolling/Gameplay",
			"ue5_project/Variant_SideScrolling/Interfaces",
			"ue5_project/Variant_SideScrolling/UI"
		});

		// Uncomment if you are using Slate UI
		// PrivateDependencyModuleNames.AddRange(new string[] { "Slate", "SlateCore" });

		// Uncomment if you are using online features
		// PrivateDependencyModuleNames.Add("OnlineSubsystem");

		// To include OnlineSubsystemSteam, add it to the plugins section in your uproject file with the Enabled attribute set to true
	}
}
